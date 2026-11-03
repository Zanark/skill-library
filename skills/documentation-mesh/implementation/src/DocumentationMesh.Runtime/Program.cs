using System.Diagnostics;
using System.ComponentModel;
using System.Globalization;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace DocumentationMesh;

internal static class Program
{
    private const string Version = "0.1.0";
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };
    private static readonly JsonSerializerOptions CacheJsonOptions = new(JsonOptions) { WriteIndented = false };

    private static readonly Regex HeadingRegex = new(@"^(#{1,6})\s+(.+?)\s*#*\s*$", RegexOptions.Compiled);
    private static readonly Regex SetextRegex = new(@"^\s*(=+|-+)\s*$", RegexOptions.Compiled);
    private static readonly Regex InlineLinkRegex = new(@"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+[""'][^""']*[""'])?\)", RegexOptions.Compiled);
    private static readonly Regex ImageRegex = new(@"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[""'][^""']*[""'])?\)", RegexOptions.Compiled);
    private static readonly Regex ReferenceLinkRegex = new(@"(?<!!)\[([^\]]+)\]\[([^\]]*)\]", RegexOptions.Compiled);
    private static readonly Regex ReferenceDefinitionRegex = new(@"^\s*\[([^\]]+)\]:\s*(\S+)", RegexOptions.Compiled);
    private static readonly Regex HtmlLinkRegex = new(@"<a\b[^>]*\bhref=[""']([^""']+)[""']", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex HtmlAnchorRegex = new(@"<(?:a|span|div|h[1-6])\b[^>]*(?:id|name)=[""']([^""']+)[""']", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex WikiLinkRegex = new(@"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", RegexOptions.Compiled);
    private static readonly Regex UrlRegex = new(@"^[a-z][a-z0-9+.-]*:", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex SecretRegex = new(@"\b(token|password|secret|api[_ -]?key|authorization|connectionstring|sas)\b\s*[:=]\s*([^\s,;]+)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex CodePathRegex = new(@"(?i)(?<![\w])(?:[a-z]:\\|\.{0,2}[\\/])[^`""'<>\r\n]+?\.(?:cs|ts|tsx|js|jsx|py|go|rs|java|cpp|c|h|hpp|ps1|sh|json|ya?ml|xml|sql|kql)", RegexOptions.Compiled);
    private static readonly Regex WorkItemRegex = new(@"https?://[^)\s]+/_workitems/edit/(\d+)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PullRequestRegex = new(@"https?://[^)\s]+/pullrequest/(\d+)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex IncidentRegex = new(@"https?://portal\.microsofticm\.com/[^)\s]*/incidents/details/(\d+)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex CommandRegex = new(@"(?<![\w-])(?:az|git|dotnet|npm|npx|python|python3|pwsh|powershell|kubectl|helm|curl)\s+[^`\r\n]{1,160}", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly HashSet<string> EdgeClasses = ["explicit", "structural", "inferred", "incidental"];
    private static readonly HashSet<string> ConfidenceLevels = ["high", "medium", "low", "unknown"];

    private static int Main(string[] args)
    {
        try
        {
            if (args.Length == 1 && args[0] == "--version")
            {
                Console.WriteLine($"documentation-mesh {Version}");
                return 0;
            }

            if (args.Length == 0)
                throw new MeshException("A command is required: init, build, validate, or open");

            string command = args[0].ToLowerInvariant();
            Dictionary<string, string?> options = ParseOptions(args.Skip(1).ToArray());
            switch (command)
            {
                case "init":
                {
                    string source = Require(options, "--source");
                    string workspace = Require(options, "--workspace");
                    string configPath = Initialize(source, workspace, options.ContainsKey("--force"));
                    PrintJson(new { config = configPath, workspace = Path.GetDirectoryName(configPath)! });
                    break;
                }
                case "build":
                {
                    string config = Require(options, "--config");
                    BuildResult result = Build(Path.GetFullPath(config), options.ContainsKey("--validate"));
                    PrintJson(new
                    {
                        statistics = result.Index.Statistics,
                        outputs = new
                        {
                            index = result.Paths.Index,
                            html = result.Paths.Html,
                            digest = result.Paths.Digest,
                            cache = result.Paths.Cache
                        }
                    });
                    if (options.ContainsKey("--open"))
                        OpenReport(result.Paths.Html);
                    break;
                }
                case "validate":
                {
                    string indexPath = Path.GetFullPath(Require(options, "--index"));
                    MeshIndex index = ReadJson<MeshIndex>(indexPath);
                    ValidateIndex(index);
                    PrintJson(new { valid = true, index = indexPath });
                    break;
                }
                case "open":
                    OpenReport(Path.GetFullPath(Require(options, "--html")));
                    break;
                default:
                    throw new MeshException($"Unknown command: {args[0]}");
            }
            return 0;
        }
        catch (Exception ex) when (ex is MeshException or IOException or UnauthorizedAccessException or JsonException or InvalidOperationException or ArgumentException or NotSupportedException or Win32Exception)
        {
            Console.Error.WriteLine($"documentation-mesh: {ex.Message}");
            return 1;
        }
    }

    private static Dictionary<string, string?> ParseOptions(string[] args)
    {
        var result = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < args.Length; i++)
        {
            string key = args[i];
            if (!key.StartsWith("--", StringComparison.Ordinal))
                throw new MeshException($"Unexpected argument: {key}");
            if (key is "--force" or "--validate" or "--open")
                result[key] = null;
            else
            {
                if (++i >= args.Length || args[i].StartsWith("--", StringComparison.Ordinal))
                    throw new MeshException($"Missing value for {key}");
                result[key] = args[i];
            }
        }
        return result;
    }

    private static string Require(Dictionary<string, string?> options, string name) =>
        options.TryGetValue(name, out string? value) && !string.IsNullOrWhiteSpace(value)
            ? value
            : throw new MeshException($"Missing required option {name}");

    private static string Initialize(string sourceValue, string workspaceValue, bool force)
    {
        string source = Path.GetFullPath(sourceValue);
        string workspace = Path.GetFullPath(workspaceValue);
        if (!Directory.Exists(source))
            throw new MeshException($"Source directory does not exist: {source}");
        if (!Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories)
                .Any(path => Path.GetExtension(path).Equals(".md", StringComparison.OrdinalIgnoreCase) ||
                             Path.GetExtension(path).Equals(".mdx", StringComparison.OrdinalIgnoreCase)))
            throw new MeshException($"No Markdown or MDX files found under {source}");
        if (IsInside(workspace, source))
            throw new MeshException("Generated workspace must remain outside the source collection");

        string configPath = Path.Combine(workspace, "config.json");
        if (File.Exists(configPath) && !force)
            return configPath;

        Directory.CreateDirectory(workspace);
        Config config = JsonSerializer.Deserialize<Config>(ReadResource("DocumentationMesh.config.default.json"), JsonOptions)
                        ?? throw new MeshException("Bundled default configuration is invalid");
        config.SourceRoots = [source];
        config.WorkspaceLocation = workspace;
        config.RuntimeVersion = Version;
        config.PluginVersion = Version;
        AtomicWrite(configPath, Serialize(config));
        AtomicWrite(Path.Combine(workspace, "README.md"), ReadResource("DocumentationMesh.workspace-readme.md"));
        return configPath;
    }

    private static BuildResult Build(string configPath, bool validate)
    {
        Stopwatch stopwatch = Stopwatch.StartNew();
        Config config = ValidateConfig(ReadJson<Config>(configPath), configPath);
        (List<DiscoveredFile> files, List<SkippedFile> discoverySkips) = DiscoverFiles(config);
        if (files.Count == 0)
            throw new MeshException("No Markdown or MDX files matched the configured scope");

        (List<Document> documents, CacheFile cache, int reused, int reparsed, List<SkippedFile> parseSkips) = ParseWithCache(files, config);
        GitProvenance provenance = BuildGitProvenance(documents, config);
        AssignInheritedOwners(documents, provenance);
        (List<Edge> explicitEdges, List<BrokenReference> broken, List<ExternalLink> external) = ResolveInternalLinks(documents);
        (List<Section> sections, List<Edge> navigationEdges) = ParseNavigation(documents);
        (List<Entity> entities, List<Edge> entityEdges) = EntityRecords(documents, config.MaximumOptionalEntityNodes);
        List<Edge> allEdges = [.. explicitEdges, .. navigationEdges, .. entityEdges];
        List<HealthFinding> findings = HealthFindings(documents, explicitEdges, broken);
        Graph graph = BuildGraph(documents, sections, entities, allEdges);
        List<TimelineEvent> timeline = BuildTimeline(documents);
        List<string> warnings = [.. provenance.Warnings];
        if (parseSkips.Count + discoverySkips.Count > 0)
            warnings.Add($"{parseSkips.Count + discoverySkips.Count} source files were skipped");
        if (config.SessionProvenanceEnabled)
            warnings.Add("Local session provenance is enabled but this runtime version indexes Git provenance only.");

        stopwatch.Stop();
        var index = new MeshIndex
        {
            SchemaVersion = 1,
            GeneratedAt = DateTimeOffset.Now.ToString("O", CultureInfo.InvariantCulture),
            GeneratorVersion = Version,
            SourceRoots = [.. config.ResolvedSourceRoots],
            Configuration = config.ToPublicDictionary(),
            Statistics = new Statistics
            {
                DocumentCount = documents.Count,
                SectionCount = sections.Count,
                EntityCount = entities.Count,
                GraphNodeCount = graph.Nodes.Count,
                GraphEdgeCount = graph.Edges.Count,
                DefaultEdgeCount = graph.Edges.Count(edge => edge.ShownByDefault),
                OptionalEdgeCount = graph.Edges.Count(edge => !edge.ShownByDefault),
                HealthFindingCount = findings.Count,
                ExternalLinkCount = external.Count,
                CacheReused = reused,
                CacheReparsed = reparsed,
                BuildSeconds = Math.Round(stopwatch.Elapsed.TotalSeconds, 3)
            },
            Documents = documents,
            Sections = sections,
            Entities = entities,
            Graph = graph,
            Timeline = timeline,
            HealthFindings = findings,
            GitProvenance = provenance,
            ArtifactProvenance = new ArtifactProvenance(),
            ExternalLinks = external,
            Warnings = warnings,
            SkippedFiles = [.. discoverySkips, .. parseSkips]
        };

        if (validate)
            ValidateIndex(index);

        string indexPath = Path.Combine(config.OutputPath, "documentation-index.json");
        string htmlPath = Path.Combine(config.OutputPath, "documentation-mesh.html");
        string digestPath = Path.Combine(config.OutputPath, "DOCUMENTATION-MESH.md");
        AtomicWrite(indexPath, Serialize(index));
        AtomicWrite(htmlPath, RenderHtml(index));
        AtomicWrite(digestPath, RenderDigest(index));
        AtomicWrite(config.CacheFullPath, JsonSerializer.Serialize(cache, CacheJsonOptions));
        return new BuildResult(index, new OutputPaths(indexPath, htmlPath, digestPath, config.CacheFullPath));
    }

    private static Config ValidateConfig(Config config, string configPath)
    {
        if (config.SchemaVersion != 1)
            throw new MeshException($"Unsupported config schemaVersion: {config.SchemaVersion}");
        if (config.SourceRoots is null || config.SourceRoots.Count == 0)
            throw new MeshException("sourceRoots must contain at least one directory");
        if (config.IncludeGlobs is null || config.ExcludeGlobs is null ||
            string.IsNullOrWhiteSpace(config.OutputDirectory) || string.IsNullOrWhiteSpace(config.CachePath) ||
            string.IsNullOrWhiteSpace(config.RuntimeVersion) || string.IsNullOrWhiteSpace(config.PluginVersion))
            throw new MeshException("Configuration is missing required keys");

        string workspace = Path.GetFullPath(Path.GetDirectoryName(configPath) ?? ".");
        config.ConfigFullPath = Path.GetFullPath(configPath);
        config.WorkspacePath = workspace;
        config.ResolvedSourceRoots = config.SourceRoots.Select(value => ResolvePath(workspace, value)).ToList();
        List<string> missing = config.ResolvedSourceRoots.Where(path => !Directory.Exists(path)).ToList();
        if (missing.Count > 0)
            throw new MeshException($"Source roots do not exist: {string.Join(", ", missing)}");
        config.OutputPath = ResolvePath(workspace, config.OutputDirectory);
        config.CacheFullPath = ResolvePath(workspace, config.CachePath);
        if (!IsInside(config.OutputPath, workspace) || !IsInside(config.CacheFullPath, workspace))
            throw new MeshException("Output and cache paths must remain inside the generated workspace");
        if (config.ResolvedSourceRoots.Any(root => IsInside(workspace, root)))
            throw new MeshException("Generated workspace must not be inside a configured source root");
        return config;
    }

    private static (List<DiscoveredFile>, List<SkippedFile>) DiscoverFiles(Config config)
    {
        var selected = new List<DiscoveredFile>();
        var skipped = new List<SkippedFile>();
        var names = config.ResolvedSourceRoots.GroupBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
            .ToDictionary(group => group.Key, group => group.Count(), StringComparer.OrdinalIgnoreCase);
        for (int rootIndex = 0; rootIndex < config.ResolvedSourceRoots.Count; rootIndex++)
        {
            string root = config.ResolvedSourceRoots[rootIndex];
            string baseName = Path.GetFileName(root);
            string rootName = names[baseName] == 1 ? baseName : $"{baseName}-{rootIndex + 1}";
            foreach (string file in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories))
            {
                string relative = NormalizePath(Path.GetRelativePath(root, file));
                if (MatchesAny(relative, config.ExcludeGlobs) || !MatchesAny(relative, config.IncludeGlobs))
                    continue;
                string full = Path.GetFullPath(file);
                if (!IsInside(full, root))
                {
                    skipped.Add(new SkippedFile { Path = full, Reason = "Path escaped configured source root" });
                    continue;
                }
                selected.Add(new DiscoveredFile(full, root, rootName));
            }
        }
        selected.Sort((left, right) => StringComparer.Ordinal.Compare(
            Canonical($"{left.RootName}/{NormalizePath(Path.GetRelativePath(left.Root, left.Path))}"),
            Canonical($"{right.RootName}/{NormalizePath(Path.GetRelativePath(right.Root, right.Path))}")));
        return (selected, skipped);
    }

    private static (List<Document>, CacheFile, int, int, List<SkippedFile>) ParseWithCache(List<DiscoveredFile> files, Config config)
    {
        CacheFile oldCache;
        try
        {
            oldCache = File.Exists(config.CacheFullPath) ? ReadJson<CacheFile>(config.CacheFullPath) : new CacheFile();
            if (oldCache.SchemaVersion != 1 || oldCache.GeneratorVersion != Version)
                oldCache = new CacheFile();
        }
        catch
        {
            oldCache = new CacheFile();
        }

        var newCache = new CacheFile();
        var documents = new List<Document>();
        var skipped = new List<SkippedFile>();
        int reused = 0;
        int reparsed = 0;
        foreach (DiscoveredFile file in files)
        {
            string key = Canonical($"{file.RootName}/{NormalizePath(Path.GetRelativePath(file.Root, file.Path))}");
            try
            {
                var info = new FileInfo(file.Path);
                var signature = new FileSignature { Size = info.Length, MtimeNs = info.LastWriteTimeUtc.Ticks * 100 };
                Document document;
                if (oldCache.Files.TryGetValue(key, out CacheEntry? cached) && cached.Signature.Equals(signature))
                {
                    document = cached.Document;
                    reused++;
                }
                else
                {
                    document = ParseDocument(file, config);
                    reparsed++;
                }
                documents.Add(document);
                newCache.Files[key] = new CacheEntry { Signature = signature, Document = document };
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                skipped.Add(new SkippedFile { Path = file.Path, Reason = ex.Message });
            }
        }
        documents.Sort((left, right) => StringComparer.Ordinal.Compare(Canonical(left.CollectionPath), Canonical(right.CollectionPath)));
        return (documents, newCache, reused, reparsed, skipped);
    }

    private static Document ParseDocument(DiscoveredFile file, Config config)
    {
        string text = File.ReadAllText(file.Path, Encoding.UTF8);
        string normalizedSource = text.Replace("\r\n", "\n", StringComparison.Ordinal).Replace('\r', '\n');
        string[] lines = normalizedSource.Length == 0
            ? []
            : (normalizedSource.EndsWith('\n') ? normalizedSource[..^1] : normalizedSource).Split('\n');
        string relative = NormalizePath(Path.GetRelativePath(file.Root, file.Path));
        string collectionPath = $"{file.RootName}/{relative}";
        (Dictionary<string, object?> frontmatter, int contentStart, List<string> warnings) = ParseFrontmatter(lines);
        var headings = new List<Heading>();
        var links = new List<LinkReference>();
        var images = new List<ImageReference>();
        var codeReferences = new List<ValueReference>();
        var commands = new List<ValueReference>();
        var workItems = new List<IdReference>();
        var pullRequests = new List<IdReference>();
        var incidents = new List<IdReference>();
        var definitions = new Dictionary<string, (string Target, int Line, string Raw)>(StringComparer.OrdinalIgnoreCase);
        var anchors = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var bodyLines = new List<string>();
        bool fence = false;
        char fenceMarker = '\0';
        int mermaidCount = 0;
        string currentHeading = "";
        int currentHeadingLine = 0;
        string documentId = StableId("doc", Canonical(collectionPath));

        for (int i = 0; i < lines.Length; i++)
        {
            int lineNumber = i + 1;
            string raw = lines[i];
            string stripped = raw.Trim();
            Match fenceMatch = Regex.Match(raw, @"^\s*(```+|~~~+)\s*([A-Za-z0-9_-]*)");
            if (fenceMatch.Success)
            {
                char marker = fenceMatch.Groups[1].Value[0];
                if (!fence)
                {
                    fence = true;
                    fenceMarker = marker;
                    if (fenceMatch.Groups[2].Value.Equals("mermaid", StringComparison.OrdinalIgnoreCase))
                        mermaidCount++;
                }
                else if (marker == fenceMarker)
                {
                    fence = false;
                    fenceMarker = '\0';
                }
                continue;
            }
            if (fence || lineNumber <= contentStart)
                continue;

            Match headingMatch = HeadingRegex.Match(raw);
            if (headingMatch.Success)
            {
                string headingText = Regex.Replace(headingMatch.Groups[2].Value, @"\s+\{#.*\}\s*$", "").Trim();
                Match explicitAnchor = Regex.Match(headingMatch.Groups[2].Value, @"\{#([^}]+)\}\s*$");
                string anchor = explicitAnchor.Success ? explicitAnchor.Groups[1].Value : Slugify(headingText);
                currentHeading = headingText;
                currentHeadingLine = lineNumber;
                anchors.Add(anchor);
                headings.Add(new Heading
                {
                    Id = StableId("sec", $"{collectionPath}#{anchor}"),
                    DocumentId = documentId,
                    Level = headingMatch.Groups[1].Value.Length,
                    Title = headingText,
                    Anchor = anchor,
                    Line = lineNumber,
                    Evidence = EvidenceFor(collectionPath, lineNumber, raw)
                });
                continue;
            }
            if (i > 0 && SetextRegex.IsMatch(raw) && !string.IsNullOrWhiteSpace(lines[i - 1]))
            {
                currentHeading = lines[i - 1].Trim();
                currentHeadingLine = lineNumber - 1;
                string anchor = Slugify(currentHeading);
                anchors.Add(anchor);
                headings.Add(new Heading
                {
                    Id = StableId("sec", $"{collectionPath}#{anchor}"),
                    DocumentId = documentId,
                    Level = stripped.StartsWith('=') ? 1 : 2,
                    Title = currentHeading,
                    Anchor = anchor,
                    Line = lineNumber - 1,
                    Evidence = EvidenceFor(collectionPath, lineNumber - 1, lines[i - 1], lineNumber)
                });
            }

            foreach (Match anchorMatch in HtmlAnchorRegex.Matches(raw))
                anchors.Add(Slugify(WebUtility.HtmlDecode(anchorMatch.Groups[1].Value)));

            Match definition = ReferenceDefinitionRegex.Match(raw);
            if (definition.Success)
                definitions[definition.Groups[1].Value.Trim()] = (definition.Groups[2].Value, lineNumber, raw);

            foreach (Match match in ImageRegex.Matches(raw))
                images.Add(new ImageReference { Target = match.Groups[2].Value, Alt = match.Groups[1].Value, Line = lineNumber, Evidence = EvidenceFor(collectionPath, lineNumber, raw) });
            string withoutImages = ImageRegex.Replace(raw, "");
            foreach ((string label, string target) in ExtractInlineLinks(withoutImages))
                links.Add(NewLink(label, target, lineNumber, currentHeading, currentHeadingLine, "markdown", collectionPath, raw));
            foreach (Match match in HtmlLinkRegex.Matches(raw))
                links.Add(NewLink("", match.Groups[1].Value, lineNumber, currentHeading, currentHeadingLine, "html", collectionPath, raw));
            string withoutUrls = Regex.Replace(raw, @"https?://\S+", "", RegexOptions.IgnoreCase);
            foreach (Match match in WikiLinkRegex.Matches(withoutUrls))
            {
                string wikiTarget = match.Groups[1].Value.Trim();
                string normalizedWikiTarget = Regex.Replace(wikiTarget, @"[^A-Za-z]", "");
                bool looksLikeEmbeddedData = Regex.IsMatch(wikiTarget, "[,\"'{}]");
                if (!looksLikeEmbeddedData && !normalizedWikiTarget.Equals("TOC", StringComparison.OrdinalIgnoreCase))
                    links.Add(NewLink(wikiTarget, wikiTarget, lineNumber, currentHeading, currentHeadingLine, "wiki", collectionPath, raw));
            }
            foreach (Match match in ReferenceLinkRegex.Matches(raw))
                links.Add(new LinkReference
                {
                    Label = match.Groups[1].Value,
                    ReferenceKey = string.IsNullOrWhiteSpace(match.Groups[2].Value) ? match.Groups[1].Value.Trim().ToLowerInvariant() : match.Groups[2].Value.Trim().ToLowerInvariant(),
                    Target = "",
                    Line = lineNumber,
                    Heading = currentHeading,
                    HeadingLine = currentHeadingLine,
                    Syntax = "reference",
                    Evidence = EvidenceFor(collectionPath, lineNumber, raw)
                });
            foreach (Match match in CodePathRegex.Matches(raw))
                codeReferences.Add(NewValue(match.Value, lineNumber, collectionPath, raw));
            foreach (Match match in CommandRegex.Matches(raw))
                commands.Add(NewValue(Redact(match.Value, 180), lineNumber, collectionPath, raw));
            AddIds(WorkItemRegex, raw, lineNumber, collectionPath, workItems);
            AddIds(PullRequestRegex, raw, lineNumber, collectionPath, pullRequests);
            AddIds(IncidentRegex, raw, lineNumber, collectionPath, incidents);
            if (Regex.IsMatch(raw, @"\[[^\]]*\]\([^)]*$"))
                warnings.Add($"Malformed Markdown link at line {lineNumber}");
            if (!string.IsNullOrWhiteSpace(stripped) && !stripped.StartsWith('#') && !stripped.StartsWith('>') && !stripped.StartsWith('|'))
                bodyLines.Add(stripped);
        }

        if (fence)
            warnings.Add("Unclosed code fence");
        foreach (LinkReference link in links.Where(link => !string.IsNullOrWhiteSpace(link.ReferenceKey)))
        {
            if (definitions.TryGetValue(link.ReferenceKey!, out var definition))
            {
                link.Target = definition.Target;
                link.DefinitionEvidence = EvidenceFor(collectionPath, definition.Line, definition.Raw);
            }
            else
            {
                link.UnresolvedReference = true;
            }
        }

        string title = GetFrontmatterString(frontmatter, "title");
        if (string.IsNullOrWhiteSpace(title) && headings.Count > 0)
            title = headings[0].Title;
        if (string.IsNullOrWhiteSpace(title))
            title = Path.GetFileNameWithoutExtension(file.Path).Replace('-', ' ').Replace('_', ' ').Trim();
        string owner = FirstNonEmpty(GetFrontmatterString(frontmatter, "owner"), GetFrontmatterString(frontmatter, "owners"), GetFrontmatterString(frontmatter, "author"));
        List<string> tags = GetFrontmatterList(frontmatter, "tags");
        string status = GetFrontmatterString(frontmatter, "status").ToLowerInvariant();
        if (status is not ("deprecated" or "archived" or "draft" or "generated" or "active"))
        {
            string lowered = collectionPath.ToLowerInvariant();
            status = lowered.Contains("deprecated") ? "deprecated" :
                     lowered.Contains("archived") || lowered.Contains("archive") ? "archived" :
                     lowered.Contains("draft") ? "draft" :
                     lowered.Contains("generated") ? "generated" :
                     lowered.Contains("active") ? "active" : "unknown";
        }
        if (MatchesAny(collectionPath, config.GeneratedDocumentGlobs))
            status = "generated";
        else if (MatchesAny(collectionPath, config.ArchivedDocumentGlobs))
            status = "archived";
        string summary = Redact(string.Join(" ", bodyLines.Take(3)), 520);
        string purpose = bodyLines.Select(line => Redact(line, 360)).FirstOrDefault(line => line.Length > 35) ?? "";
        string family = relative.Contains('/') ? relative.Split('/')[0] : file.RootName;
        return new Document
        {
            Id = documentId,
            Title = title,
            SourceRoot = file.Root,
            RootName = file.RootName,
            RelativePath = relative,
            CollectionPath = collectionPath,
            AbsolutePath = file.Path,
            FileType = Path.GetExtension(file.Path).TrimStart('.').ToLowerInvariant(),
            Family = family,
            ParentSection = NormalizePath(Path.GetDirectoryName(relative) ?? "."),
            Summary = summary,
            Purpose = purpose,
            Audience = GetFrontmatterString(frontmatter, "audience"),
            Status = status,
            Owner = owner,
            Frontmatter = frontmatter,
            Tags = tags.Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToList(),
            Headings = headings,
            Anchors = anchors.Order(StringComparer.Ordinal).ToList(),
            Links = links,
            Images = images,
            CodeReferences = codeReferences,
            Commands = commands,
            WorkItems = workItems,
            PullRequests = pullRequests,
            Incidents = incidents,
            HasDiagrams = mermaidCount > 0,
            MermaidBlocks = mermaidCount,
            Warnings = warnings.Distinct(StringComparer.Ordinal).ToList(),
            ContentHash = Sha256(text),
            NormalizedText = Redact(string.Join(" ", bodyLines), 12000).ToLowerInvariant(),
            LineCount = lines.Length
        };
    }

    private static (Dictionary<string, object?>, int, List<string>) ParseFrontmatter(string[] lines)
    {
        var values = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        var warnings = new List<string>();
        if (lines.Length == 0 || lines[0].Trim() != "---")
            return (values, 0, warnings);
        int end = Array.FindIndex(lines, 1, line => line.Trim() == "---");
        if (end < 0)
            return (values, 0, ["Unclosed YAML frontmatter"]);
        string? currentList = null;
        for (int i = 1; i < end; i++)
        {
            string stripped = lines[i].Trim();
            if (string.IsNullOrWhiteSpace(stripped) || stripped.StartsWith('#'))
                continue;
            if (stripped.StartsWith("- ", StringComparison.Ordinal) && currentList is not null)
            {
                ((List<string>)values[currentList]!).Add(stripped[2..].Trim().Trim('"', '\''));
                continue;
            }
            int colon = lines[i].IndexOf(':');
            if (colon < 0)
            {
                warnings.Add($"Unparsed frontmatter line: {Redact(lines[i], 120)}");
                continue;
            }
            string key = lines[i][..colon].Trim();
            string raw = lines[i][(colon + 1)..].Trim();
            if (string.IsNullOrWhiteSpace(key))
                continue;
            if (string.IsNullOrWhiteSpace(raw))
            {
                values[key] = new List<string>();
                currentList = key;
            }
            else if (raw.StartsWith('[') && raw.EndsWith(']'))
            {
                values[key] = raw[1..^1].Split(',').Select(value => value.Trim().Trim('"', '\'')).Where(value => value.Length > 0).ToList();
                currentList = null;
            }
            else if (bool.TryParse(raw, out bool boolean))
            {
                values[key] = boolean;
                currentList = null;
            }
            else
            {
                values[key] = raw.Trim('"', '\'');
                currentList = null;
            }
        }
        return (values, end + 1, warnings);
    }

    private static GitProvenance BuildGitProvenance(List<Document> documents, Config config)
    {
        if (!config.GitHistoryEnabled)
            return new GitProvenance { Enabled = false };
        var output = new GitProvenance();
        var repositoryBySourceRoot = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (string sourceRoot in documents.Select(document => document.SourceRoot).Distinct(StringComparer.OrdinalIgnoreCase))
        {
            ProcessResult probe = RunProcess("git", ["-C", sourceRoot, "rev-parse", "--show-toplevel"]);
            if (probe.ExitCode != 0)
            {
                output.Warnings.Add($"Git history unavailable for {sourceRoot}");
                continue;
            }
            repositoryBySourceRoot[sourceRoot] = Path.GetFullPath(probe.StandardOutput.Trim());
        }

        foreach (IGrouping<string, Document> group in documents
                     .Where(document => repositoryBySourceRoot.ContainsKey(document.SourceRoot))
                     .GroupBy(document => repositoryBySourceRoot[document.SourceRoot], StringComparer.OrdinalIgnoreCase)
                     .OrderBy(group => group.Key, StringComparer.OrdinalIgnoreCase))
        {
            string repository = group.Key;
            output.Repositories.Add(repository);
            ProcessResult log = RunProcess("git",
            [
                "-C", repository, "log", "--reverse", "--date=iso-strict",
                "--format=@@@%H%x09%aI%x09%an%x09%ae%x09%s", "--name-status", "--"
            ]);
            if (log.ExitCode != 0)
            {
                output.Warnings.Add($"Git log failed for {repository}: {Redact(log.StandardError)}");
                continue;
            }

            var history = new Dictionary<string, List<GitHistoryEvent>>(StringComparer.OrdinalIgnoreCase);
            GitHistoryEvent? current = null;
            foreach (string raw in log.StandardOutput.Split('\n'))
            {
                string line = raw.TrimEnd('\r');
                if (line.StartsWith("@@@", StringComparison.Ordinal))
                {
                    string[] parts = line[3..].Split('\t', 5);
                    current = parts.Length == 5
                        ? new GitHistoryEvent(parts[0], parts[1], parts[2], parts[3], Redact(parts[4], 220), "")
                        : null;
                    continue;
                }
                if (current is null || string.IsNullOrWhiteSpace(line))
                    continue;
                string[] fields = line.Split('\t');
                if (fields.Length < 2)
                    continue;
                string targetPath = fields[^1];
                string key = Canonical(targetPath);
                if (!history.TryGetValue(key, out List<GitHistoryEvent>? events))
                    history[key] = events = [];
                events.Add(current with { ChangeType = fields[0][0].ToString() });
            }

            foreach (Document document in group)
            {
                string relative = NormalizePath(Path.GetRelativePath(repository, document.AbsolutePath));
                if (!history.TryGetValue(Canonical(relative), out List<GitHistoryEvent>? events) || events.Count == 0)
                    continue;
                GitHistoryEvent first = events[0];
                GitHistoryEvent last = events[^1];
                var record = new GitDocumentRecord
                {
                    Creation = new GitMoment { Timestamp = first.Timestamp, Source = "git-first-commit", Confidence = "high", Commit = first.Commit, Author = first.Author },
                    LastMeaningfulUpdate = new GitMoment { Timestamp = last.Timestamp, Source = "git-last-commit", Confidence = "high", Commit = last.Commit, Author = last.Author, Subject = last.Subject },
                    Contributors = events.Select(item => item.Author).Where(value => value.Length > 0).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToList(),
                    CommitCount = events.Count
                };
                output.Documents[document.Id] = record;
                document.EarliestKnownCreationDate = first.Timestamp;
                document.LastMeaningfulUpdate = last.Timestamp;
                document.DateProvenance = "git";
                document.Contributors = record.Contributors;
            }
        }
        foreach (Document document in documents.Where(document => !output.Documents.ContainsKey(document.Id)))
        {
            document.EarliestKnownCreationDate = "";
            document.LastMeaningfulUpdate = File.GetLastWriteTimeUtc(document.AbsolutePath).ToString("O", CultureInfo.InvariantCulture);
            document.DateProvenance = "filesystem-modification";
            document.Contributors = [];
        }
        output.Repositories = output.Repositories.Distinct(StringComparer.OrdinalIgnoreCase).Order(StringComparer.OrdinalIgnoreCase).ToList();
        return output;
    }

    private static void AssignInheritedOwners(List<Document> documents, GitProvenance provenance)
    {
        var cache = new Dictionary<string, (string Owner, Evidence Evidence)?>(StringComparer.OrdinalIgnoreCase);
        foreach (Document document in documents.Where(document => string.IsNullOrWhiteSpace(document.Owner)))
        {
            string sourcePath = Path.GetFullPath(document.AbsolutePath);
            string repository = provenance.Repositories
                .Where(root => IsInside(sourcePath, root))
                .OrderByDescending(root => root.Length)
                .FirstOrDefault() ?? Path.GetFullPath(document.SourceRoot);
            string? current = Path.GetDirectoryName(sourcePath);
            while (current is not null && IsInside(current, repository))
            {
                string ownersPath = Path.Combine(current, "owners.txt");
                if (!cache.TryGetValue(ownersPath, out (string Owner, Evidence Evidence)? inherited))
                {
                    inherited = null;
                    if (File.Exists(ownersPath))
                    {
                        var aliases = new List<string>();
                        int firstLine = 0;
                        int lineNumber = 0;
                        foreach (string raw in File.ReadLines(ownersPath))
                        {
                            lineNumber++;
                            string value = raw.Trim();
                            if (value.Length == 0 || value.StartsWith(';'))
                                continue;
                            if (firstLine == 0)
                                firstLine = lineNumber;
                            aliases.Add(value.TrimStart('*'));
                        }
                        if (aliases.Count > 0)
                        {
                            string owner = string.Join(", ", aliases.Distinct(StringComparer.OrdinalIgnoreCase).Order(StringComparer.OrdinalIgnoreCase));
                            inherited = (owner, EvidenceFor(ownersPath, firstLine, string.Join(", ", aliases)));
                        }
                    }
                    cache[ownersPath] = inherited;
                }
                if (inherited is not null)
                {
                    document.Owner = inherited.Value.Owner;
                    document.OwnerEvidence = inherited.Value.Evidence;
                    document.OwnerSource = "inherited-owners-file";
                    break;
                }
                if (Path.GetFullPath(current).Equals(Path.GetFullPath(repository), StringComparison.OrdinalIgnoreCase))
                    break;
                current = Path.GetDirectoryName(current);
            }
        }
    }

    private static (List<Edge>, List<BrokenReference>, List<ExternalLink>) ResolveInternalLinks(List<Document> documents)
    {
        var absolute = documents.ToDictionary(document => Canonical(Path.GetFullPath(document.AbsolutePath)), StringComparer.Ordinal);
        var edges = new List<Edge>();
        var broken = new List<BrokenReference>();
        var external = new List<ExternalLink>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (Document document in documents)
        {
            foreach (LinkReference link in document.Links)
            {
                string target = (link.Target ?? "").Trim().Trim('<', '>');
                if (target.Length == 0 || target.StartsWith('#'))
                {
                    string anchor = target.StartsWith('#') ? Uri.UnescapeDataString(target[1..]) : "";
                    if (anchor.Length > 0 && !document.Anchors.Contains(Slugify(anchor), StringComparer.OrdinalIgnoreCase))
                        broken.Add(new BrokenReference { Type = "broken-anchor", DocumentId = document.Id, Target = target, Evidence = link.Evidence });
                    continue;
                }
                if (UrlRegex.IsMatch(target) || target.StartsWith("//", StringComparison.Ordinal))
                {
                    external.Add(new ExternalLink { DocumentId = document.Id, Url = target, Evidence = link.Evidence });
                    continue;
                }
                string decoded = Uri.UnescapeDataString(target);
                string[] partition = decoded.Split('#', 2);
                string pathPart = partition[0].Split('?', 2)[0].Replace('/', Path.DirectorySeparatorChar);
                string anchorPart = partition.Length > 1 ? partition[1] : "";
                string candidate = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(document.AbsolutePath)!, pathPart));
                var candidates = new List<string> { candidate };
                if (!Path.HasExtension(candidate))
                {
                    candidates.Add(candidate + ".md");
                    candidates.Add(Path.Combine(candidate, "index.md"));
                    candidates.Add(Path.Combine(candidate, "README.md"));
                }
                Document? targetDocument = candidates.Select(value => absolute.GetValueOrDefault(Canonical(value))).FirstOrDefault(value => value is not null);
                if (targetDocument is null)
                {
                    string extension = Path.GetExtension(pathPart);
                    if (extension.Length > 0 &&
                        !extension.Equals(".md", StringComparison.OrdinalIgnoreCase) &&
                        !extension.Equals(".mdx", StringComparison.OrdinalIgnoreCase) &&
                        candidates.Any(File.Exists))
                        continue;
                    string findingType = extension.Length > 0 &&
                                         !extension.Equals(".md", StringComparison.OrdinalIgnoreCase) &&
                                         !extension.Equals(".mdx", StringComparison.OrdinalIgnoreCase)
                        ? "missing-asset"
                        : "broken-link";
                    broken.Add(new BrokenReference { Type = findingType, DocumentId = document.Id, Target = target, Evidence = link.Evidence });
                    continue;
                }
                if (anchorPart.Length > 0 && !targetDocument.Anchors.Contains(Slugify(anchorPart), StringComparer.OrdinalIgnoreCase))
                    broken.Add(new BrokenReference { Type = "broken-anchor", DocumentId = document.Id, TargetDocumentId = targetDocument.Id, Target = target, Evidence = link.Evidence });

                string heading = link.Heading.ToLowerInvariant();
                string label = link.Label.ToLowerInvariant();
                string relation = "document-link";
                string reason = "The source document contains a direct internal link to the target document.";
                if (ContainsAny(heading, label, "see also", "related"))
                {
                    relation = "see-also";
                    reason = "The source document explicitly lists the target in a related or see-also context.";
                }
                else if (ContainsAny(heading, label, "prerequisite", "before you begin"))
                {
                    relation = "prerequisite";
                    reason = "The source document explicitly identifies the target as prerequisite material.";
                }
                else if (ContainsAny(heading, label, "next step", "next steps"))
                {
                    relation = "next-step";
                    reason = "The source document explicitly identifies the target as a next step.";
                }
                else if (ContainsAny(heading, label, "deprecated", "replacement", "replaced by"))
                {
                    relation = "replacement";
                    reason = "The source document explicitly links the target in a replacement or deprecation context.";
                }
                string signature = $"{document.Id}|{targetDocument.Id}|{relation}|{link.Line}";
                if (!seen.Add(signature))
                    continue;
                edges.Add(new Edge
                {
                    Id = StableId("edge", signature),
                    Source = document.Id,
                    Target = targetDocument.Id,
                    Type = relation,
                    RelationshipClass = "explicit",
                    Confidence = "high",
                    Reason = reason,
                    Evidence = [link.Evidence],
                    Directional = true,
                    ExtractionMethod = $"{link.Syntax}-link",
                    ShownByDefault = true
                });
            }
        }
        return (edges.OrderBy(edge => edge.Id, StringComparer.Ordinal).ToList(), broken, external);
    }

    private static (List<Section>, List<Edge>) ParseNavigation(List<Document> documents)
    {
        var byAbsolute = documents.ToDictionary(document => Canonical(document.AbsolutePath), StringComparer.Ordinal);
        var sections = new Dictionary<string, Section>(StringComparer.Ordinal);
        var edges = new List<Edge>();
        IEnumerable<string> tocPaths = documents.Select(document => document.SourceRoot).Distinct(StringComparer.OrdinalIgnoreCase)
            .SelectMany(root => Directory.EnumerateFiles(root, "toc.y*ml", SearchOption.AllDirectories))
            .Distinct(StringComparer.OrdinalIgnoreCase).Order(StringComparer.OrdinalIgnoreCase);
        foreach (string toc in tocPaths)
        {
            string[] lines;
            try { lines = File.ReadAllLines(toc, Encoding.UTF8); }
            catch { continue; }
            var stack = new List<(int Indent, string Id)>();
            for (int i = 0; i < lines.Length; i++)
            {
                int lineNumber = i + 1;
                string raw = lines[i];
                Match name = Regex.Match(raw, @"^(\s*)-\s+name:\s*(.+?)\s*$", RegexOptions.IgnoreCase);
                if (name.Success)
                {
                    int indent = name.Groups[1].Value.Length;
                    string title = name.Groups[2].Value.Trim().Trim('"', '\'');
                    stack = stack.Where(entry => entry.Indent < indent).ToList();
                    string parentId = stack.Count > 0 ? stack[^1].Id : "";
                    string id = StableId("nav", $"{toc}|{indent}|{title}|{lineNumber}");
                    var section = new Section
                    {
                        Id = id,
                        Type = "navigation-section",
                        Title = title,
                        SourceFile = toc,
                        Line = lineNumber,
                        ParentId = parentId,
                        Evidence = EvidenceFor(toc, lineNumber, raw)
                    };
                    sections[id] = section;
                    if (parentId.Length > 0)
                        edges.Add(NewStructuralEdge(parentId, id, "contains", "The navigation file nests this section beneath its parent.", toc, lineNumber, raw, $"contains|{lineNumber}"));
                    stack.Add((indent, id));
                    continue;
                }
                Match href = Regex.Match(raw, @"^(\s+)href:\s*(.+?)\s*$", RegexOptions.IgnoreCase);
                if (!href.Success || stack.Count == 0)
                    continue;
                string target = href.Groups[2].Value.Trim().Trim('"', '\'');
                if (UrlRegex.IsMatch(target))
                    continue;
                string candidate = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(toc)!, Uri.UnescapeDataString(target.Split('#', 2)[0])));
                if (!byAbsolute.TryGetValue(Canonical(candidate), out Document? document))
                    continue;
                string sectionId = stack[^1].Id;
                edges.Add(new Edge
                {
                    Id = StableId("edge", $"{sectionId}|{document.Id}|toc-membership|{lineNumber}"),
                    Source = sectionId,
                    Target = document.Id,
                    Type = "toc-membership",
                    RelationshipClass = "structural",
                    Confidence = "high",
                    Reason = "The persisted navigation file explicitly lists this document under the section.",
                    Evidence = [EvidenceFor(toc, lineNumber, raw)],
                    Directional = true,
                    ExtractionMethod = "toc-yaml",
                    ShownByDefault = false,
                    Caveat = "Navigation membership is structural and hidden in the core document graph."
                });
            }
        }
        return (sections.Values.OrderBy(section => section.Id, StringComparer.Ordinal).ToList(), edges.OrderBy(edge => edge.Id, StringComparer.Ordinal).ToList());
    }

    private static (List<Entity>, List<Edge>) EntityRecords(List<Document> documents, int limit)
    {
        var entities = new Dictionary<string, Entity>(StringComparer.Ordinal);
        var edges = new List<Edge>();
        foreach (Document document in documents)
        {
            AddEntityReferences(document, "code-file", document.CodeReferences.Select(value => (value.Value, value.Line, value.Evidence)), entities, edges);
            AddEntityReferences(document, "command", document.Commands.Select(value => (value.Value, value.Line, value.Evidence)), entities, edges);
            AddEntityReferences(document, "work-item", document.WorkItems.Select(value => (value.Id, value.Line, value.Evidence)), entities, edges);
            AddEntityReferences(document, "pull-request", document.PullRequests.Select(value => (value.Id, value.Line, value.Evidence)), entities, edges);
            AddEntityReferences(document, "incident", document.Incidents.Select(value => (value.Id, value.Line, value.Evidence)), entities, edges);
        }
        List<Entity> ranked = entities.Values.OrderByDescending(entity => entity.References)
            .ThenBy(entity => entity.Type, StringComparer.Ordinal).ThenBy(entity => entity.Name, StringComparer.OrdinalIgnoreCase).Take(Math.Max(0, limit)).ToList();
        HashSet<string> allowed = ranked.Select(entity => entity.Id).ToHashSet(StringComparer.Ordinal);
        return (ranked, edges.Where(edge => allowed.Contains(edge.Target)).OrderBy(edge => edge.Id, StringComparer.Ordinal).ToList());
    }

    private static List<HealthFinding> HealthFindings(List<Document> documents, List<Edge> edges, List<BrokenReference> broken)
    {
        var findings = new List<HealthFinding>();
        Dictionary<string, int> inbound = edges.Where(edge => edge.ShownByDefault).GroupBy(edge => edge.Target).ToDictionary(group => group.Key, group => group.Count());
        Dictionary<string, int> outbound = edges.Where(edge => edge.ShownByDefault).GroupBy(edge => edge.Source).ToDictionary(group => group.Key, group => group.Count());
        Dictionary<string, Document> byId = documents.ToDictionary(document => document.Id, StringComparer.Ordinal);
        foreach (BrokenReference issue in broken)
            findings.Add(new HealthFinding
            {
                Id = StableId("health", Serialize(issue)),
                Type = issue.Type,
                Severity = "error",
                DocumentId = issue.DocumentId,
                Title = $"{TitleCase(issue.Type.Replace('-', ' '))}: {issue.Target}",
                Reason = "The referenced internal target or anchor could not be resolved.",
                Evidence = [issue.Evidence]
            });
        foreach (Document document in documents)
        {
            Evidence evidence = EvidenceFor(document.CollectionPath, 1, document.Title);
            if (string.IsNullOrWhiteSpace(document.Owner))
                findings.Add(NewFinding("missing-owner", "info", document.Id, "No explicit owner metadata", "The document does not explicitly declare an owner or author.", evidence));
            bool hasInbound = inbound.ContainsKey(document.Id);
            bool hasOutbound = outbound.ContainsKey(document.Id);
            if (!hasInbound && !hasOutbound)
                findings.Add(NewFinding("orphan", "warning", document.Id, "Orphan document", "No strong incoming or outgoing document relationship was found.", evidence));
            else if (!hasInbound)
                findings.Add(NewFinding("no-inbound-links", "info", document.Id, "No strong inbound links", "No other document strongly links to this document.", evidence));
            if (!hasOutbound)
                findings.Add(NewFinding("no-outbound-links", "info", document.Id, "No strong outbound links", "This document does not strongly link to another indexed document.", evidence));
            foreach (string warning in document.Warnings)
            {
                string type = warning.Contains("frontmatter", StringComparison.OrdinalIgnoreCase) ? "invalid-frontmatter" : "invalid-markdown";
                HealthFinding finding = NewFinding(type, "warning", document.Id, warning, "The parser found malformed or unsupported persisted syntax.", evidence);
                finding.Id = StableId("health", $"{type}|{document.Id}|{warning}");
                findings.Add(finding);
            }
        }

        var pairs = new HashSet<string>(StringComparer.Ordinal);
        foreach (IGrouping<string, Document> group in documents.GroupBy(document => document.ContentHash).Where(group => group.Count() > 1))
        {
            List<Document> values = group.OrderBy(document => document.Id, StringComparer.Ordinal).ToList();
            for (int i = 0; i + 1 < values.Count; i++)
                pairs.Add(Pair(values[i].Id, values[i + 1].Id));
        }
        List<(Document Document, ulong Hash)> simhashes = documents.Where(document => document.NormalizedText.Length > 240)
            .Select(document => (document, SimHash(document.NormalizedText))).ToList();
        foreach (IGrouping<ulong, (Document Document, ulong Hash)> bucket in simhashes.GroupBy(item => item.Hash >> 48))
        {
            var values = bucket.ToList();
            for (int i = 0; i < values.Count; i++)
                for (int j = i + 1; j < values.Count; j++)
                    if (HammingDistance(values[i].Hash, values[j].Hash) <= 3)
                        pairs.Add(Pair(values[i].Document.Id, values[j].Document.Id));
        }
        foreach (string pair in pairs.Order(StringComparer.Ordinal))
        {
            string[] ids = pair.Split('|');
            Document left = byId[ids[0]];
            Document right = byId[ids[1]];
            string type = left.ContentHash == right.ContentHash ? "duplicate-document" : "near-duplicate-document";
            findings.Add(new HealthFinding
            {
                Id = StableId("health", $"{type}|{left.Id}|{right.Id}"),
                Type = type,
                Severity = "warning",
                DocumentId = left.Id,
                RelatedDocumentId = right.Id,
                Title = TitleCase(type.Replace('-', ' ')),
                Reason = "The normalized document content is identical or has a very close SimHash.",
                Evidence = [EvidenceFor(left.CollectionPath, 1, left.Title), EvidenceFor(right.CollectionPath, 1, right.Title)]
            });
        }
        return findings.OrderBy(finding => finding.Type, StringComparer.Ordinal).ThenBy(finding => finding.DocumentId, StringComparer.Ordinal).ThenBy(finding => finding.Id, StringComparer.Ordinal).ToList();
    }

    private static Graph BuildGraph(List<Document> documents, List<Section> sections, List<Entity> entities, List<Edge> edges)
    {
        var degree = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (Edge edge in edges)
        {
            degree[edge.Source] = degree.GetValueOrDefault(edge.Source) + 1;
            degree[edge.Target] = degree.GetValueOrDefault(edge.Target) + 1;
        }
        var nodes = documents.Select(document => new GraphNode
        {
            Id = document.Id,
            Type = "document",
            Label = document.Title,
            Path = document.CollectionPath,
            Family = document.Family,
            OutlineColor = FamilyColor(document.Family),
            Status = document.Status,
            Date = string.IsNullOrWhiteSpace(document.EarliestKnownCreationDate) ? document.LastMeaningfulUpdate : document.EarliestKnownCreationDate,
            DateSource = document.DateProvenance,
            DateConfidence = document.DateProvenance == "git" ? "high" : "low",
            Degree = degree.GetValueOrDefault(document.Id),
            ShownByDefault = true
        }).ToList();
        nodes.AddRange(sections.Select(section => new GraphNode
        {
            Id = section.Id, Type = "section", Label = section.Title, Path = section.SourceFile, Family = "Navigation",
            OutlineColor = FamilyColor("Navigation"), Status = "active", Date = "", DateSource = "unknown", DateConfidence = "unknown",
            Degree = degree.GetValueOrDefault(section.Id), ShownByDefault = false
        }));
        nodes.AddRange(entities.Select(entity => new GraphNode
        {
            Id = entity.Id, Type = entity.Type, Label = entity.Name, Path = "", Family = entity.Type,
            OutlineColor = FamilyColor(entity.Type), Status = "unknown", Date = "", DateSource = "unknown", DateConfidence = "unknown",
            Degree = degree.GetValueOrDefault(entity.Id), ShownByDefault = false
        }));
        return new Graph
        {
            Nodes = nodes.OrderBy(node => node.Id, StringComparer.Ordinal).ToList(),
            Edges = edges.OrderBy(edge => edge.Id, StringComparer.Ordinal).ToList()
        };
    }

    private static List<TimelineEvent> BuildTimeline(List<Document> documents)
    {
        var timeline = new List<TimelineEvent>();
        foreach (Document document in documents)
        {
            if (!string.IsNullOrWhiteSpace(document.EarliestKnownCreationDate))
                timeline.Add(new TimelineEvent
                {
                    Id = StableId("event", $"created|{document.Id}"), DocumentId = document.Id, Timestamp = document.EarliestKnownCreationDate,
                    Type = "created", Source = document.DateProvenance, Confidence = document.DateProvenance == "git" ? "high" : "low", Title = $"Created: {document.Title}"
                });
            if (!string.IsNullOrWhiteSpace(document.LastMeaningfulUpdate))
                timeline.Add(new TimelineEvent
                {
                    Id = StableId("event", $"updated|{document.Id}|{document.LastMeaningfulUpdate}"), DocumentId = document.Id, Timestamp = document.LastMeaningfulUpdate,
                    Type = "updated", Source = document.DateProvenance, Confidence = document.DateProvenance == "git" ? "high" : "low", Title = $"Updated: {document.Title}"
                });
        }
        return timeline.OrderBy(item => string.IsNullOrWhiteSpace(item.Timestamp) ? "9999" : item.Timestamp, StringComparer.Ordinal).ThenBy(item => item.Id, StringComparer.Ordinal).ToList();
    }

    private static void ValidateIndex(MeshIndex index)
    {
        if (index.SchemaVersion != 1 || string.IsNullOrWhiteSpace(index.GeneratedAt) || string.IsNullOrWhiteSpace(index.GeneratorVersion) ||
            index.SourceRoots is null || index.Documents is null || index.Sections is null || index.Entities is null ||
            index.Graph is null || index.HealthFindings is null)
            throw new MeshException("Index is missing required fields");
        List<string> nodeIds = index.Graph.Nodes.Select(node => node.Id).ToList();
        List<string> edgeIds = index.Graph.Edges.Select(edge => edge.Id).ToList();
        if (nodeIds.Count != nodeIds.Distinct(StringComparer.Ordinal).Count())
            throw new MeshException("Duplicate graph node IDs detected");
        if (edgeIds.Count != edgeIds.Distinct(StringComparer.Ordinal).Count())
            throw new MeshException("Duplicate graph edge IDs detected");
        HashSet<string> nodeIdSet = nodeIds.ToHashSet(StringComparer.Ordinal);
        if (index.Documents.Any(document => !nodeIdSet.Contains(document.Id)))
            throw new MeshException("One or more documents are missing graph nodes");
        foreach (Edge edge in index.Graph.Edges)
        {
            if (!nodeIdSet.Contains(edge.Source) || !nodeIdSet.Contains(edge.Target))
                throw new MeshException($"Dangling graph edge: {edge.Id}");
            if (!EdgeClasses.Contains(edge.RelationshipClass))
                throw new MeshException($"Invalid relationship class on {edge.Id}");
            if (!ConfidenceLevels.Contains(edge.Confidence))
                throw new MeshException($"Invalid confidence on {edge.Id}");
            foreach (Evidence evidence in edge.Evidence)
                if (evidence.LineStart < 1 || evidence.LineEnd < evidence.LineStart)
                    throw new MeshException($"Invalid evidence line range on {edge.Id}");
        }
    }

    private static string RenderHtml(MeshIndex index)
    {
        string css = ReadResource("DocumentationMesh.dashboard.css");
        string javascript = ReadResource("DocumentationMesh.dashboard.js");
        string vendor = ReadResource("DocumentationMesh.vendor.min.js");
        string payload = JsonForScript(index);
        return $"""
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Documentation Mesh</title><style>{css}</style></head>
<body><header><h1>Documentation Mesh</h1><div class="subtitle">Evidence-backed offline documentation intelligence · generated {WebUtility.HtmlEncode(index.GeneratedAt)}</div>
<nav class="tabs"><button class="tab active" data-view="catalogue">Catalogue</button><button class="tab" data-view="graph">Knowledge graph</button><button class="tab" data-view="health">Health</button><button class="tab" data-view="timeline">Timeline</button><button class="tab" data-view="provenance">Provenance</button></nav></header>
<main>
<section id="catalogue" class="view active"><div id="summary" class="metrics"></div><div id="catalogue-controls" class="toolbar"></div><div id="documents"></div></section>
<section id="graph" class="view"><div id="graph-controls" class="toolbar"></div><div id="animation-status"></div><div class="graph-shell"><div id="graph-canvas"></div><aside id="inspector" class="panel"><h2>Select a node or edge</h2></aside></div></section>
<section id="health" class="view"><div id="health-summary" class="metrics"></div><div id="health-controls" class="toolbar"></div><div id="health-findings"></div></section>
<section id="timeline" class="view"><div id="timeline-controls" class="toolbar"></div><div id="timeline-events"></div></section>
<section id="provenance" class="view"><div class="panel"><h2>Source and artifact provenance</h2><input id="provenance-search" placeholder="Search path, filename, commit, author, or artifact"><div id="provenance-results"></div></div></section>
</main><script>{vendor}</script><script>window.DOCUMENTATION_MESH_INDEX={payload};</script><script>{javascript}</script></body></html>
""";
    }

    private static string RenderDigest(MeshIndex index)
    {
        Dictionary<string, int> health = index.HealthFindings.GroupBy(finding => finding.Type).ToDictionary(group => group.Key, group => group.Count());
        var lines = new List<string>
        {
            "# Documentation Mesh — Startup Digest", "", $"> Generated: {index.GeneratedAt}",
            "> Source documentation is read-only. The JSON index is the source of truth.", "", "## Portfolio summary", "",
            $"- Source roots: {index.SourceRoots.Count}", $"- Documents: {index.Statistics.DocumentCount}",
            $"- Graph: {index.Statistics.GraphNodeCount} nodes / {index.Statistics.GraphEdgeCount} edges",
            $"- Strong default relationships: {index.Statistics.DefaultEdgeCount}", $"- Optional relationships: {index.Statistics.OptionalEdgeCount}",
            $"- Cache: {index.Statistics.CacheReused} reused / {index.Statistics.CacheReparsed} reparsed",
            $"- Broken links: {health.GetValueOrDefault("broken-link")}", $"- Broken anchors: {health.GetValueOrDefault("broken-anchor")}",
            $"- Orphans: {health.GetValueOrDefault("orphan")}", "", "## Largest documentation families", ""
        };
        lines.AddRange(index.Documents.GroupBy(document => document.Family).OrderByDescending(group => group.Count()).ThenBy(group => group.Key, StringComparer.Ordinal).Take(12).Select(group => $"- {group.Key}: {group.Count()}"));
        lines.AddRange(["", "## Known limitations and warnings", ""]);
        lines.AddRange(index.Warnings.Count > 0 ? index.Warnings.Select(warning => $"- {warning}") : ["- None recorded."]);
        lines.AddRange(["", "## Hydration protocol", "", "1. Read this digest for portfolio scope and health.", "2. Use `documentation-index.json` for exact evidence, paths, graph data, and provenance.", "3. Treat source Markdown as read-only.", ""]);
        return string.Join(Environment.NewLine, lines);
    }

    private static void OpenReport(string path)
    {
        if (!File.Exists(path))
            throw new MeshException($"Report does not exist: {path}");
        Process.Start(new ProcessStartInfo(Path.GetFullPath(path)) { UseShellExecute = true });
    }

    private static string ReadResource(string name)
    {
        using Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
                              ?? throw new MeshException($"Bundled resource is missing: {name}");
        using var reader = new StreamReader(stream, Encoding.UTF8);
        return reader.ReadToEnd();
    }

    private static void AtomicWrite(string path, string content)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        string temporary = Path.Combine(Path.GetDirectoryName(path)!, $".{Path.GetFileName(path)}.{Guid.NewGuid():N}.tmp");
        try
        {
            File.WriteAllText(temporary, content, new UTF8Encoding(false));
            File.Move(temporary, path, true);
        }
        finally
        {
            if (File.Exists(temporary))
                File.Delete(temporary);
        }
    }

    private static T ReadJson<T>(string path)
    {
        try
        {
            return JsonSerializer.Deserialize<T>(File.ReadAllText(path, Encoding.UTF8), JsonOptions)
                   ?? throw new MeshException($"Expected a JSON object in {path}");
        }
        catch (Exception ex) when (ex is IOException or JsonException)
        {
            throw new MeshException($"Cannot read JSON file {path}: {ex.Message}");
        }
    }

    private static string Serialize<T>(T value) => JsonSerializer.Serialize(value, JsonOptions);
    private static void PrintJson<T>(T value) => Console.WriteLine(Serialize(value));
    private static string JsonForScript<T>(T value) => JsonSerializer.Serialize(value, JsonOptions)
        .Replace("<", "\\u003c", StringComparison.Ordinal).Replace("\u2028", "\\u2028", StringComparison.Ordinal).Replace("\u2029", "\\u2029", StringComparison.Ordinal);
    private static string ResolvePath(string basePath, string value) => Path.GetFullPath(Path.IsPathRooted(value) ? value : Path.Combine(basePath, value));
    private static string NormalizePath(string value) => value.Replace('\\', '/');
    private static string Canonical(string value) => NormalizePath(value).Trim('/').ToLowerInvariant();
    private static bool IsInside(string candidate, string parent)
    {
        string relative = Path.GetRelativePath(Path.GetFullPath(parent), Path.GetFullPath(candidate));
        return relative == "." || (!Path.IsPathRooted(relative) && relative != ".." && !relative.StartsWith($"..{Path.DirectorySeparatorChar}", StringComparison.Ordinal));
    }

    private static bool MatchesAny(string path, IEnumerable<string> patterns) => patterns.Any(pattern => GlobMatches(path, pattern));
    private static bool GlobMatches(string path, string pattern)
    {
        path = NormalizePath(path);
        pattern = NormalizePath(pattern);
        var regex = new StringBuilder("^");
        for (int i = 0; i < pattern.Length; i++)
        {
            char current = pattern[i];
            if (current == '*')
            {
                bool doubleStar = i + 1 < pattern.Length && pattern[i + 1] == '*';
                if (doubleStar)
                {
                    i++;
                    if (i + 1 < pattern.Length && pattern[i + 1] == '/')
                    {
                        i++;
                        regex.Append("(?:.*/)?");
                    }
                    else regex.Append(".*");
                }
                else regex.Append("[^/]*");
            }
            else if (current == '?') regex.Append("[^/]");
            else regex.Append(Regex.Escape(current.ToString()));
        }
        regex.Append('$');
        return Regex.IsMatch(path, regex.ToString(), RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    }

    private static string StableId(string prefix, string value) => $"{prefix}-{Sha256(value)[..16]}";
    private static string Sha256(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
    private static string Redact(string value, int limit = 480)
    {
        value = SecretRegex.Replace(value, match => $"{match.Groups[1].Value}=[redacted]");
        value = Regex.Replace(value, @"\s+", " ").Trim();
        return value.Length <= limit ? value : value[..(limit - 1)].TrimEnd() + "...";
    }
    private static string Slugify(string value)
    {
        value = Regex.Replace(value, "<[^>]+>", "");
        value = Regex.Replace(value.ToLowerInvariant(), @"[^\p{L}\p{N}_\s-]", "");
        return Regex.Replace(value, @"[-\s]+", "-").Trim('-');
    }
    private static Evidence EvidenceFor(string path, int line, string text, int? endLine = null) =>
        new() { SourceFile = path, LineStart = line, LineEnd = endLine ?? line, Excerpt = Redact(text) };
    private static IEnumerable<(string Label, string Target)> ExtractInlineLinks(string line)
    {
        int cursor = 0;
        while (cursor < line.Length)
        {
            int labelStart = line.IndexOf('[', cursor);
            if (labelStart < 0)
                yield break;
            if (labelStart > 0 && line[labelStart - 1] == '!')
            {
                cursor = labelStart + 1;
                continue;
            }
            int labelEnd = line.IndexOf("](", labelStart, StringComparison.Ordinal);
            if (labelEnd < 0)
                yield break;
            int targetStart = labelEnd + 2;
            int depth = 1;
            char quote = '\0';
            int index = targetStart;
            for (; index < line.Length; index++)
            {
                char character = line[index];
                if (quote != '\0')
                {
                    if (character == quote && (index == targetStart || line[index - 1] != '\\'))
                        quote = '\0';
                    continue;
                }
                if (character is '"' or '\'')
                {
                    quote = character;
                    continue;
                }
                if (character == '(')
                    depth++;
                else if (character == ')' && --depth == 0)
                    break;
            }
            if (depth != 0)
                yield break;
            string label = line[(labelStart + 1)..labelEnd];
            string target = line[targetStart..index].Trim();
            Match title = Regex.Match(target, @"^(.+?)\s+[""'][^""']*[""']$");
            if (title.Success)
                target = title.Groups[1].Value.Trim();
            if (target.StartsWith('<') && target.EndsWith('>') && target.Length > 2)
                target = target[1..^1];
            if (target.Length > 0)
                yield return (label, target);
            cursor = index + 1;
        }
    }
    private static LinkReference NewLink(string label, string target, int line, string heading, int headingLine, string syntax, string path, string raw) =>
        new() { Label = label, Target = target, Line = line, Heading = heading, HeadingLine = headingLine, Syntax = syntax, Evidence = EvidenceFor(path, line, raw) };
    private static ValueReference NewValue(string value, int line, string path, string raw) =>
        new() { Value = value, Line = line, Evidence = EvidenceFor(path, line, raw) };
    private static void AddIds(Regex regex, string raw, int line, string path, List<IdReference> target)
    {
        foreach (Match match in regex.Matches(raw))
            target.Add(new IdReference { Id = match.Groups[1].Value, Line = line, Evidence = EvidenceFor(path, line, raw) });
    }
    private static string GetFrontmatterString(Dictionary<string, object?> values, string key)
    {
        if (!values.TryGetValue(key, out object? value) || value is null) return "";
        if (value is string text) return text;
        if (value is List<string> list) return string.Join(", ", list);
        if (value is JsonElement element)
        {
            if (element.ValueKind == JsonValueKind.String) return element.GetString() ?? "";
            if (element.ValueKind == JsonValueKind.Array) return string.Join(", ", element.EnumerateArray().Select(item => item.ToString()));
        }
        return value.ToString() ?? "";
    }
    private static List<string> GetFrontmatterList(Dictionary<string, object?> values, string key)
    {
        if (!values.TryGetValue(key, out object? value) || value is null) return [];
        if (value is List<string> list) return list;
        if (value is string text) return text.Split(',').Select(item => item.Trim()).Where(item => item.Length > 0).ToList();
        if (value is JsonElement element && element.ValueKind == JsonValueKind.Array) return element.EnumerateArray().Select(item => item.ToString()).ToList();
        return [];
    }
    private static string FirstNonEmpty(params string[] values) => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? "";
    private static bool ContainsAny(string left, string right, params string[] words) => words.Any(word => left.Contains(word, StringComparison.Ordinal) || right.Contains(word, StringComparison.Ordinal));
    private static string TitleCase(string value) => CultureInfo.InvariantCulture.TextInfo.ToTitleCase(value);
    private static string FamilyColor(string name)
    {
        uint value = Convert.ToUInt32(Sha256(name.ToLowerInvariant())[..8], 16);
        return $"hsl({value % 360} 72% 62%)";
    }
    private static string Pair(string left, string right) => StringComparer.Ordinal.Compare(left, right) <= 0 ? $"{left}|{right}" : $"{right}|{left}";
    private static ulong SimHash(string text)
    {
        Dictionary<string, int> counts = Regex.Matches(text.ToLowerInvariant(), @"[a-z0-9_]{3,}").Select(match => match.Value)
            .GroupBy(word => word).ToDictionary(group => group.Key, group => group.Count());
        var vector = new int[64];
        foreach ((string word, int weight) in counts)
        {
            ulong hash = Convert.ToUInt64(Sha256(word)[..16], 16);
            for (int bit = 0; bit < 64; bit++) vector[bit] += (hash & (1UL << bit)) != 0 ? weight : -weight;
        }
        ulong result = 0;
        for (int bit = 0; bit < 64; bit++) if (vector[bit] >= 0) result |= 1UL << bit;
        return result;
    }
    private static int HammingDistance(ulong value)
    {
        int count = 0;
        while (value != 0) { value &= value - 1; count++; }
        return count;
    }
    private static int HammingDistance(ulong left, ulong right) => HammingDistance(left ^ right);
    private static ProcessResult RunProcess(string fileName, IEnumerable<string> arguments)
    {
        using var process = new Process { StartInfo = new ProcessStartInfo(fileName) { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true } };
        foreach (string argument in arguments) process.StartInfo.ArgumentList.Add(argument);
        try
        {
            process.Start();
            string output = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            process.WaitForExit();
            return new ProcessResult(process.ExitCode, output, error);
        }
        catch
        {
            return new ProcessResult(1, "", "");
        }
    }
    private static Edge NewStructuralEdge(string source, string target, string type, string reason, string path, int line, string raw, string signature) =>
        new()
        {
            Id = StableId("edge", $"{source}|{target}|{signature}"), Source = source, Target = target, Type = type,
            RelationshipClass = "structural", Confidence = "high", Reason = reason, Evidence = [EvidenceFor(path, line, raw)],
            Directional = true, ExtractionMethod = "toc-yaml", ShownByDefault = false, Caveat = "Structural navigation containment is not semantic similarity."
        };
    private static void AddEntityReferences(Document document, string type, IEnumerable<(string Value, int Line, Evidence Evidence)> references, Dictionary<string, Entity> entities, List<Edge> edges)
    {
        int index = 0;
        foreach ((string value, int line, Evidence evidence) in references)
        {
            string normalized = value.Trim();
            if (normalized.Length == 0) continue;
            string key = $"{type}|{normalized.ToLowerInvariant()}";
            if (!entities.TryGetValue(key, out Entity? entity))
            {
                entity = new Entity { Id = StableId("ent", key), Type = type, Name = normalized };
                entities[key] = entity;
            }
            entity.References++;
            edges.Add(new Edge
            {
                Id = StableId("edge", $"{document.Id}|{entity.Id}|{type}|{line}|{index++}|{normalized}"),
                Source = document.Id, Target = entity.Id, Type = "references", RelationshipClass = "explicit", Confidence = "high",
                Reason = $"The document explicitly references this {type.Replace('-', ' ')}.", Evidence = [evidence], Directional = true,
                ExtractionMethod = "exact-reference", ShownByDefault = false, Caveat = "Referenced entities are available only in expanded graph detail."
            });
        }
    }
    private static HealthFinding NewFinding(string type, string severity, string documentId, string title, string reason, Evidence evidence) =>
        new() { Id = StableId("health", $"{type}|{documentId}"), Type = type, Severity = severity, DocumentId = documentId, Title = title, Reason = reason, Evidence = [evidence] };

    private sealed class MeshException(string message) : Exception(message);
    private sealed record BuildResult(MeshIndex Index, OutputPaths Paths);
    private sealed record OutputPaths(string Index, string Html, string Digest, string Cache);
    private sealed record DiscoveredFile(string Path, string Root, string RootName);
    private sealed record ProcessResult(int ExitCode, string StandardOutput, string StandardError);
    private sealed record GitHistoryEvent(string Commit, string Timestamp, string Author, string Email, string Subject, string ChangeType);

    private sealed class Config
    {
        public int SchemaVersion { get; set; }
        public List<string> SourceRoots { get; set; } = [];
        public List<string> IncludeGlobs { get; set; } = [];
        public List<string> ExcludeGlobs { get; set; } = [];
        public List<string> GeneratedDocumentGlobs { get; set; } = [];
        public List<string> ArchivedDocumentGlobs { get; set; } = [];
        public string OutputDirectory { get; set; } = "";
        public string CachePath { get; set; } = "";
        public bool GitHistoryEnabled { get; set; } = true;
        public bool SessionProvenanceEnabled { get; set; }
        public string SessionStateRoot { get; set; } = "";
        public int HistoryWindowDays { get; set; } = 365;
        public int FreshDays { get; set; } = 180;
        public int AgingDays { get; set; } = 365;
        public int StaleDays { get; set; } = 730;
        public int MaximumOptionalEntityNodes { get; set; } = 2500;
        public string DefaultEvidenceLevel { get; set; } = "strong";
        public string DefaultDetailLevel { get; set; } = "documents";
        public string BrowserExecutablePath { get; set; } = "";
        public string WorkspaceLocation { get; set; } = "";
        public string RuntimeVersion { get; set; } = "";
        public string PluginVersion { get; set; } = "";
        public bool AllowWorkspaceInitialization { get; set; } = true;
        [JsonIgnore] public string ConfigFullPath { get; set; } = "";
        [JsonIgnore] public string WorkspacePath { get; set; } = "";
        [JsonIgnore] public List<string> ResolvedSourceRoots { get; set; } = [];
        [JsonIgnore] public string OutputPath { get; set; } = "";
        [JsonIgnore] public string CacheFullPath { get; set; } = "";
        public Dictionary<string, object?> ToPublicDictionary() => new()
        {
            ["schemaVersion"] = SchemaVersion, ["sourceRoots"] = SourceRoots, ["includeGlobs"] = IncludeGlobs, ["excludeGlobs"] = ExcludeGlobs,
            ["generatedDocumentGlobs"] = GeneratedDocumentGlobs, ["archivedDocumentGlobs"] = ArchivedDocumentGlobs, ["outputDirectory"] = OutputDirectory,
            ["cachePath"] = CachePath, ["gitHistoryEnabled"] = GitHistoryEnabled, ["sessionProvenanceEnabled"] = SessionProvenanceEnabled,
            ["historyWindowDays"] = HistoryWindowDays, ["freshDays"] = FreshDays, ["agingDays"] = AgingDays, ["staleDays"] = StaleDays,
            ["maximumOptionalEntityNodes"] = MaximumOptionalEntityNodes, ["defaultEvidenceLevel"] = DefaultEvidenceLevel,
            ["defaultDetailLevel"] = DefaultDetailLevel, ["browserExecutablePath"] = BrowserExecutablePath, ["workspaceLocation"] = WorkspaceLocation,
            ["runtimeVersion"] = RuntimeVersion, ["pluginVersion"] = PluginVersion, ["allowWorkspaceInitialization"] = AllowWorkspaceInitialization
        };
    }

    private sealed class MeshIndex
    {
        public int SchemaVersion { get; set; }
        public string GeneratedAt { get; set; } = "";
        public string GeneratorVersion { get; set; } = "";
        public List<string> SourceRoots { get; set; } = [];
        public Dictionary<string, object?> Configuration { get; set; } = [];
        public Statistics Statistics { get; set; } = new();
        public List<Document> Documents { get; set; } = [];
        public List<Section> Sections { get; set; } = [];
        public List<Entity> Entities { get; set; } = [];
        public Graph Graph { get; set; } = new();
        public List<TimelineEvent> Timeline { get; set; } = [];
        public List<HealthFinding> HealthFindings { get; set; } = [];
        public GitProvenance GitProvenance { get; set; } = new();
        public ArtifactProvenance ArtifactProvenance { get; set; } = new();
        public List<ExternalLink> ExternalLinks { get; set; } = [];
        public List<string> Warnings { get; set; } = [];
        public List<SkippedFile> SkippedFiles { get; set; } = [];
    }
    private sealed class Statistics
    {
        public int DocumentCount { get; set; }
        public int SectionCount { get; set; }
        public int EntityCount { get; set; }
        public int GraphNodeCount { get; set; }
        public int GraphEdgeCount { get; set; }
        public int DefaultEdgeCount { get; set; }
        public int OptionalEdgeCount { get; set; }
        public int HealthFindingCount { get; set; }
        public int ExternalLinkCount { get; set; }
        public int CacheReused { get; set; }
        public int CacheReparsed { get; set; }
        public double BuildSeconds { get; set; }
    }
    private sealed class Document
    {
        public string Id { get; set; } = "";
        public string Title { get; set; } = "";
        public string SourceRoot { get; set; } = "";
        public string RootName { get; set; } = "";
        public string RelativePath { get; set; } = "";
        public string CollectionPath { get; set; } = "";
        public string AbsolutePath { get; set; } = "";
        public string FileType { get; set; } = "";
        public string Family { get; set; } = "";
        public string ParentSection { get; set; } = "";
        public string Summary { get; set; } = "";
        public string Purpose { get; set; } = "";
        public string Audience { get; set; } = "";
        public string Status { get; set; } = "unknown";
        public string Owner { get; set; } = "";
        public Evidence? OwnerEvidence { get; set; }
        public string OwnerSource { get; set; } = "";
        public Dictionary<string, object?> Frontmatter { get; set; } = [];
        public List<string> Tags { get; set; } = [];
        public List<Heading> Headings { get; set; } = [];
        public List<string> Anchors { get; set; } = [];
        public List<LinkReference> Links { get; set; } = [];
        public List<ImageReference> Images { get; set; } = [];
        public List<ValueReference> CodeReferences { get; set; } = [];
        public List<ValueReference> Commands { get; set; } = [];
        public List<IdReference> WorkItems { get; set; } = [];
        public List<IdReference> PullRequests { get; set; } = [];
        public List<IdReference> Incidents { get; set; } = [];
        public bool HasDiagrams { get; set; }
        public int MermaidBlocks { get; set; }
        public List<string> Warnings { get; set; } = [];
        public string ContentHash { get; set; } = "";
        public string NormalizedText { get; set; } = "";
        public int LineCount { get; set; }
        public string EarliestKnownCreationDate { get; set; } = "";
        public string LastMeaningfulUpdate { get; set; } = "";
        public string DateProvenance { get; set; } = "";
        public List<string> Contributors { get; set; } = [];
    }
    private sealed class Heading
    {
        public string Id { get; set; } = "";
        public string DocumentId { get; set; } = "";
        public int Level { get; set; }
        public string Title { get; set; } = "";
        public string Anchor { get; set; } = "";
        public int Line { get; set; }
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class LinkReference
    {
        public string Label { get; set; } = "";
        public string Target { get; set; } = "";
        public int Line { get; set; }
        public string Heading { get; set; } = "";
        public int HeadingLine { get; set; }
        public string Syntax { get; set; } = "";
        public Evidence Evidence { get; set; } = new();
        public string? ReferenceKey { get; set; }
        public Evidence? DefinitionEvidence { get; set; }
        public bool UnresolvedReference { get; set; }
    }
    private sealed class ValueReference
    {
        public string Value { get; set; } = "";
        public int Line { get; set; }
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class ImageReference
    {
        public string Alt { get; set; } = "";
        public string Target { get; set; } = "";
        public int Line { get; set; }
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class IdReference
    {
        public string Id { get; set; } = "";
        public int Line { get; set; }
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class Evidence
    {
        public string SourceFile { get; set; } = "";
        public int LineStart { get; set; }
        public int LineEnd { get; set; }
        public string Excerpt { get; set; } = "";
    }
    private sealed class Edge
    {
        public string Id { get; set; } = "";
        public string Source { get; set; } = "";
        public string Target { get; set; } = "";
        public string Type { get; set; } = "";
        public string RelationshipClass { get; set; } = "";
        public string Confidence { get; set; } = "";
        public string Reason { get; set; } = "";
        public List<Evidence> Evidence { get; set; } = [];
        public bool Directional { get; set; }
        public string ExtractionMethod { get; set; } = "";
        public bool ShownByDefault { get; set; }
        public string Caveat { get; set; } = "";
    }
    private sealed class Section
    {
        public string Id { get; set; } = "";
        public string Type { get; set; } = "";
        public string Title { get; set; } = "";
        public string SourceFile { get; set; } = "";
        public int Line { get; set; }
        public string ParentId { get; set; } = "";
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class Entity
    {
        public string Id { get; set; } = "";
        public string Type { get; set; } = "";
        public string Name { get; set; } = "";
        public int References { get; set; }
    }
    private sealed class Graph
    {
        public List<GraphNode> Nodes { get; set; } = [];
        public List<Edge> Edges { get; set; } = [];
    }
    private sealed class GraphNode
    {
        public string Id { get; set; } = "";
        public string Type { get; set; } = "";
        public string Label { get; set; } = "";
        public string Path { get; set; } = "";
        public string Family { get; set; } = "";
        public string OutlineColor { get; set; } = "";
        public string Status { get; set; } = "";
        public string Date { get; set; } = "";
        public string DateSource { get; set; } = "";
        public string DateConfidence { get; set; } = "";
        public int Degree { get; set; }
        public bool ShownByDefault { get; set; }
    }
    private sealed class HealthFinding
    {
        public string Id { get; set; } = "";
        public string Type { get; set; } = "";
        public string Severity { get; set; } = "";
        public string DocumentId { get; set; } = "";
        public string RelatedDocumentId { get; set; } = "";
        public string Title { get; set; } = "";
        public string Reason { get; set; } = "";
        public List<Evidence> Evidence { get; set; } = [];
    }
    private sealed class TimelineEvent
    {
        public string Id { get; set; } = "";
        public string DocumentId { get; set; } = "";
        public string Timestamp { get; set; } = "";
        public string Type { get; set; } = "";
        public string Source { get; set; } = "";
        public string Confidence { get; set; } = "";
        public string Title { get; set; } = "";
    }
    private sealed class GitProvenance
    {
        public bool Enabled { get; set; } = true;
        public List<string> Repositories { get; set; } = [];
        public Dictionary<string, GitDocumentRecord> Documents { get; set; } = [];
        public List<string> Warnings { get; set; } = [];
    }
    private sealed class GitDocumentRecord
    {
        public GitMoment Creation { get; set; } = new();
        public GitMoment LastMeaningfulUpdate { get; set; } = new();
        public List<string> Contributors { get; set; } = [];
        public int CommitCount { get; set; }
        public List<object> Renames { get; set; } = [];
    }
    private sealed class GitMoment
    {
        public string Timestamp { get; set; } = "";
        public string Source { get; set; } = "";
        public string Confidence { get; set; } = "";
        public string Commit { get; set; } = "";
        public string Author { get; set; } = "";
        public string Subject { get; set; } = "";
    }
    private sealed class ArtifactProvenance
    {
        public bool Enabled { get; set; }
        public List<object> Records { get; set; } = [];
    }
    private sealed class ExternalLink
    {
        public string DocumentId { get; set; } = "";
        public string Url { get; set; } = "";
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class BrokenReference
    {
        public string Type { get; set; } = "";
        public string DocumentId { get; set; } = "";
        public string TargetDocumentId { get; set; } = "";
        public string Target { get; set; } = "";
        public Evidence Evidence { get; set; } = new();
    }
    private sealed class SkippedFile
    {
        public string Path { get; set; } = "";
        public string Reason { get; set; } = "";
    }
    private sealed class CacheFile
    {
        public int SchemaVersion { get; set; } = 1;
        public string GeneratorVersion { get; set; } = Version;
        public Dictionary<string, CacheEntry> Files { get; set; } = [];
    }
    private sealed class CacheEntry
    {
        public FileSignature Signature { get; set; } = new();
        public Document Document { get; set; } = new();
    }
    private sealed class FileSignature : IEquatable<FileSignature>
    {
        public long Size { get; set; }
        public long MtimeNs { get; set; }
        public bool Equals(FileSignature? other) => other is not null && Size == other.Size && MtimeNs == other.MtimeNs;
        public override bool Equals(object? obj) => Equals(obj as FileSignature);
        public override int GetHashCode() => HashCode.Combine(Size, MtimeNs);
    }
}
