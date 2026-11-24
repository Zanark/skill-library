// Shared portrait drawings: live 08B plus preserved workshop comparisons.
const avatarPortraitArtDirections = Object.freeze({
  "session-fed62133-8a6d-47b0-9e2c-d2eda9fbf1ad": { theme: "pam", presentation: "feminine", flair: "restrained", expression: "kiss-wink" },
  "session-d5df688d-8707-4e35-815e-5f831a899459": { outfit: "bookbinder-apron" },
  "session-8e7d69ac-78f7-4310-8b8d-14bf8681a509-bowser": { outfit: "cartridge-varsity" },
  "session-9cbe69cd-e0d4-40c9-ac96-8c82e451fa11": { outfit: "career-pinstripe", facialHair: "goatee" },
  "session-5b1043ae-4ead-4c75-9906-3f871fa63dcb": { outfit: "director-cape" },
  "session-969d9987-a5bf-44a8-96c9-e698c3d7a0ad": { outfit: "filmfield-vest", facialHair: "stubble" },
  "session-b23fc037-0f53-4367-96f6-579b21e80be9": { outfit: "cutline-split" },
  "session-f78d59f3-e155-4e5b-8b2e-bd0607499015": { outfit: "weaver-tunic" },
  "session-b27674ed-c14a-46a6-b59d-5120fc0a519a": { outfit: "entropy-streetwear" },
  "session-efb2222e-0e0e-416a-9122-b41bc6b72512": { outfit: "relay-coat" },
  "session-e4a2585a-8b13-460d-bf1b-07e8f69e1aff": { outfit: "broadcast-jacket" },
  "session-5f0403d8-ec0e-4548-b7cd-c9120aeb3ec7": { outfit: "corrugated-stage", expression: "friendly-wink" },
  "session-003d8999-b293-4ebb-9e07-059b9faaef3e": { outfit: "application-coverall", facialHair: "boxed-beard" },
  "session-d2353248-82dc-4fec-acd8-fb8716d4aa35-modelroom": { outfit: "roomsmith-drafting" },
  "session-663618cc-e834-40fa-8ac6-597a3566c810": { outfit: "pipekeeper-yoke" },
  "session-13987e67-c8b9-4dfd-9fe3-6d4112c3950d": { outfit: "runner-track" },
  "session-3fb09634-071c-4e97-aa0d-da09c947f9d0": { outfit: "pipeline-cyclist" },
  "session-5fcc3b58-36e7-4961-b920-03283bb4cf2a": { outfit: "artifact-inspector" },
  "session-06698e54-9837-4953-9ea3-487f0ce6c865": { outfit: "archive-waistcoat", facialHair: "chevron" },
  "session-c4776b24-1cab-47a4-b085-b9d02007be28": { outfit: "report-workshirt" },
  "session-7b82fa6b-dc94-4d3e-9923-a853167266a1": { outfit: "cartographer-mantle", expression: "friendly-wink" },
  "fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064": { theme: "goth", presentation: "feminine", flair: "bold" },
  "session-718bb26f-ec71-4d8a-9543-f67727e20064": { outfit: "mesh-node-knit" },
  "session-8e7d69ac-78f7-4310-8b8d-14bf8681a509": { outfit: "editor-tabard" },
  "session-d08187e0-4409-4168-be1f-f09e69acef98": { outfit: "builder-brick-apron" },
  "session-meshboard-thread-scout": { outfit: "threadscout-cowl", facialHair: "handlebar" },
  "session-ea08b309-444c-45f5-9430-ce1b4207ce07": { outfit: "pixel-blocks" },
  "session-3bd1eee1-6bd2-4cb0-9744-04fcd8d3bd40": { outfit: "cassette-deck" },
  "session-96f84287-724b-45f0-ada4-1168c5240762": { outfit: "rig-cable-harness" },
  "session-3f8667e7-3a23-4fb9-9012-fba4281d435c": { outfit: "trickroom-harlequin" },
  "session-f69cc3b8": { outfit: "camera-safari" },
  "session-3ebcd26e-abc2-4e29-a4ee-e5d874d8a1bb": { outfit: "windowpane-coat" },
  "session-a9d82458-6aa8-4b5a-8f13-c01e53f6078a": { outfit: "desk-daywear", facialHair: "full-beard" },
});

const avatarContextArtDirections = Object.freeze({
  "ctx-157d4bd90c18": { theme: "pam", presentation: "feminine", flair: "restrained", expression: "kiss-wink" },
  "ctx-ded91077c7ca": { theme: "butler", presentation: "masculine", flair: "restrained" },
});

// Authored name motifs, not inferred biography. Panels are actual garment cuts.
const avatarNamedOutfits = Object.freeze({
  "bookbinder-apron": {
    label: "BookMaker / leather binding apron, parchment sleeves, book clasp",
    palette: ["#6c4938", "#eee1ba", "#c5a15f"],
    panels: [["M18 137L22 108L47 94L53 99L48 137ZM110 137L106 108L81 94L75 99L80 137Z", 1],
      ["M43 95L49 97L53 116H46ZM85 95L79 97L75 116H82Z", 0],
      ["M43 108H85L91 137H37Z", 0], ["M51 116H77V130H51Z", 2]],
    seams: "M45 113H83M54 119V127M58 119H73M58 123H71M26 112L31 135M102 112L97 135",
    jewel: '<path d="M56 96Q64 105 72 96M64 103V108" fill="none"/><path d="M60 107H68V113L64 111L60 113Z"/>',
    prop: '<path d="M6 29Q15 25 25 30V57Q16 52 6 55ZM25 30Q33 26 39 29V55Q31 53 25 57Z"/><path d="M10 35L21 37M10 41L21 43M10 47L20 49M25 31V55"/>',
  },
  "cartridge-varsity": {
    label: "Cartridge Keeper / arcade varsity jacket, cartridge chest rack",
    palette: ["#593e88", "#c7ddbe", "#efbd5e"],
    panels: [["M16 137L22 107L44 96L48 107L35 137ZM112 137L106 107L84 96L80 107L93 137Z", 1],
      ["M49 94Q64 102 79 94L80 101Q64 110 48 101Z", 2],
      ["M45 113H59V131H45ZM69 113H83V131H69Z", 2],
      ["M47 115H57V122H47ZM71 115H81V122H71Z", 0]],
    seams: "M64 105V136M49 126H55M73 126H79M37 134H91",
    prop: '<path d="M101 26H119V49H101Z"/><path d="M104 29H116V39H104ZM105 44H108M112 44H115M101 51V56H119V51"/>',
  },
  "career-pinstripe": {
    label: "CareerOS / stepped pinstripe suit, rising-arrow lapel",
    palette: ["#293d58", "#d9d4c6", "#d5a56d"],
    panels: [["M48 94L64 103L80 94L83 137H45Z", 1],
      ["M44 96L54 99L56 109L62 137H18L23 109ZM84 96L74 99L72 109L66 137H110L105 109Z", 0],
      ["M42 96L51 99V104H55V110H60L46 116L37 103ZM86 96L77 99V104H73V110H68L82 116L91 103Z", 2]],
    seams: "M29 108V136M35 105V136M41 117V136M87 117V136M93 105V136M99 108V136M64 107V133",
    jewel: '<path d="M83 112V104L80 107M83 104L86 107" fill="none" stroke-width="1.5"/>',
    prop: '<path d="M7 68V57H14V47H21V36H29M22 36H29V43"/><path d="M8 73H29"/>',
  },
  "director-cape": {
    label: "Original Cut / director shoulder cape, film-strip stole",
    palette: ["#302c40", "#b56358", "#e7d8bd"],
    panels: [["M48 94L56 99L51 137H18L25 106ZM80 94L72 99L77 137H110L103 106Z", 0],
      ["M27 104L48 94L58 103L39 117L17 113ZM101 104L80 94L70 103L89 117L111 113Z", 1],
      ["M54 99L60 102L58 137H49ZM74 99L68 102L70 137H79Z", 2]],
    seams: "M53 109H58M52 116H57M51 123H56M70 109H75M71 116H76M72 123H77",
    prop: '<path d="M4 35L27 29L30 39L7 45ZM7 45H31V62H7Z"/><path d="M10 34L17 41M20 31L27 38M11 49H27M11 54H22"/>',
  },
  "filmfield-vest": {
    label: "ClipFarm / field vest, film-pocket rows, wheat brooch",
    palette: ["#335d49", "#ddb97e", "#d47a54"],
    panels: [["M18 137L23 107L48 94L55 99L48 137ZM110 137L105 107L80 94L73 99L80 137Z", 1],
      ["M45 95L56 101L62 137H32L37 105ZM83 95L72 101L66 137H96L91 105Z", 0],
      ["M35 112H51V126H35ZM77 112H93V126H77Z", 2]],
    seams: "M38 115V123M43 115V123M48 115V123M80 115V123M85 115V123M90 115V123M42 99L50 108M86 99L78 108",
    jewel: '<path d="M62 112V99M62 104L58 101M62 108L66 104M62 111L58 108" fill="none"/>',
    prop: '<path d="M108 67V26M108 35L100 29M108 42L116 34M108 50L99 43M108 57L117 49"/><path d="M5 72H28V80H5ZM9 72V80M15 72V80M21 72V80"/>',
  },
  "cutline-split": {
    label: "Cutline / bias-cut two-tone shirt, scissor-chain",
    palette: ["#1e5361", "#e1a47d", "#ecdbb7"],
    panels: [["M48 94L77 137H17L22 109Z", 0],
      ["M80 94L108 110L113 137H77L48 94L56 98L64 102L74 96Z", 1],
      ["M47 94L56 99L51 106L39 100ZM81 94L72 99L77 106L89 100Z", 2]],
    seams: "M50 104L71 135M55 108L58 112M61 117L64 121M67 126L70 130M27 115L33 137",
    jewel: '<circle cx="82" cy="113" r="2" fill="none"/><circle cx="88" cy="113" r="2" fill="none"/><path d="M83 111L88 103M87 111L82 103" fill="none"/>',
    prop: '<circle cx="14" cy="39" r="5"/><circle cx="25" cy="39" r="5"/><path d="M17 35L27 17M22 35L12 17M7 62L28 53M7 68L12 66M17 64L22 62"/>',
  },
  "weaver-tunic": {
    label: "Resume Weaver / woven crossover tunic, spool pendant",
    palette: ["#7b4772", "#d9b994", "#88b7b2"],
    panels: [["M47 94L63 108L49 137H18L23 108ZM81 94L65 108L79 137H110L105 108Z", 0],
      ["M48 95L81 123L76 130L42 101ZM80 95L47 123L52 130L86 101Z", 1],
      ["M28 128H100V136H28Z", 2]],
    seams: "M32 113L43 123M37 108L48 118M85 108L96 118M80 113L91 123M38 130V135M47 130V135M56 130V135M65 130V135M74 130V135M83 130V135",
    jewel: '<path d="M58 97Q64 109 70 97" fill="none"/><path d="M61 105H67V113H61ZM59 105H69M59 113H69" fill="none"/>',
    prop: '<path d="M4 24H30V66H4ZM8 28V62M14 28V62M20 28V62M26 28V62M5 37H29M5 47H29M5 57H29"/>',
  },
  "entropy-streetwear": {
    label: "EntropyTag / jagged asymmetric streetwear, scattered tags",
    palette: ["#343344", "#cc744c", "#a9d47e"],
    panels: [["M47 94L54 99L51 137H17L21 107L34 99L37 105Z", 0],
      ["M81 94L75 99L64 116L79 137H111L106 109L94 101L90 108Z", 1],
      ["M28 112L43 108L39 120L31 118ZM79 115L94 111L99 124L86 128Z", 2],
      ["M56 100L67 105L61 118L53 110Z", 2]],
    seams: "M23 127L31 122L39 131M74 105L83 108M84 133L100 128M45 104L49 112",
    prop: '<path d="M5 28L13 19L22 30L15 39ZM104 57L119 53L121 68L108 73Z"/><circle cx="112" cy="23" r="6"/><path d="M8 68L21 51L28 62M98 39L112 47"/>',
  },
  "relay-coat": {
    label: "GenevaActions / relay-panel coat, copper switch chain",
    palette: ["#244e5e", "#b9d1c9", "#d59664"],
    panels: [["M48 94L56 99V137H18L22 110ZM80 94L72 99V137H110L106 110Z", 0],
      ["M49 94L55 98L51 109L42 104ZM79 94L73 98L77 109L86 104Z", 1],
      ["M29 113H49V129H29ZM79 113H99V129H79Z", 2]],
    seams: "M60 103V137M68 103V137M32 117H39L42 121H46M82 124H89L93 118H97M34 126H44M83 114H95",
    jewel: '<path d="M54 107Q64 122 74 107" fill="none"/><circle cx="64" cy="117" r="2"/>',
    prop: '<path d="M5 25H27V61H5ZM9 34H14L21 29M9 49H14L21 44"/><circle cx="10" cy="56" r="2"/><circle cx="22" cy="56" r="2"/>',
  },
  "broadcast-jacket": {
    label: "Intercom / radio jacket, resting headphones, signal piping",
    palette: ["#9a583e", "#ead9b6", "#546b83"],
    panels: [["M48 94L55 100L51 137H17L22 108ZM80 94L73 100L77 137H111L106 108Z", 0],
      ["M49 95L56 101L52 108L42 100ZM79 95L72 101L76 108L86 100Z", 1],
      ["M30 117H46V130H30ZM82 117H98V130H82Z", 2]],
    seams: "M63 105V137M26 108L31 112L26 116M102 108L97 112L102 116",
    jewel: '<path d="M46 99Q44 117 64 118Q84 117 82 99" fill="none" stroke-width="2"/><rect x="43" y="101" width="7" height="13" rx="3"/><rect x="78" y="101" width="7" height="13" rx="3"/>',
    prop: '<path d="M6 36H15L23 29V55L15 48H6ZM28 33Q38 42 28 51M32 27Q48 42 32 57"/>',
  },
  "corrugated-stage": {
    label: "Cardboard Continuity / folded carton armor, taped suspenders",
    palette: ["#346354", "#c99b62", "#f0d9a8"],
    panels: [["M17 137L22 109L48 94L54 99L46 137ZM111 137L106 109L80 94L74 99L82 137Z", 0],
      ["M31 109L64 103L96 110L91 137H36Z", 1],
      ["M31 109L42 98L64 103L51 115ZM64 103L84 98L97 110L78 115Z", 2],
      ["M57 108H64V137H57Z", 2]],
    seams: "M36 118L51 115M37 123L51 120M38 128L51 125M79 120L91 117M79 125L90 122M79 130L89 127M43 99L48 102M81 99L77 103",
    prop: '<path d="M4 50L16 43L30 49L18 57ZM4 50V65L18 72V57M18 57L30 49V65L18 72M5 27H23V38H5Z"/><path d="M8 31H20M8 35H16"/>',
  },
  "application-coverall": {
    label: "Apply Mechanic / fitted service coverall, wrench and document pockets",
    palette: ["#336a78", "#d7d4be", "#d49559"],
    panels: [["M50 94L58 99L64 104L70 99L78 94L83 137H45Z", 0],
      ["M49 94L58 99L54 106L43 98ZM79 94L70 99L74 106L85 98Z", 1],
      ["M30 111H48V127H30ZM79 111H98V127H79Z", 2],
      ["M32 114H45V122H32Z", 1]],
    seams: "M64 104V137M60 108H68M60 117H68M60 126H68M83 113V123M88 113V123M94 113V123",
    prop: '<path d="M10 22H27V47H10ZM14 28H23M14 34H23M14 40L17 43L23 37M8 58L14 52L19 57L13 63L11 73L6 75L4 70Z"/>',
  },
  "roomsmith-drafting": {
    label: "Roomsmith / drafting coat, triangular lapels, ruler pocket",
    palette: ["#a2684d", "#e4d7b6", "#41747b"],
    panels: [["M48 94L58 101L52 137H17L23 108ZM80 94L70 101L76 137H111L105 108Z", 0],
      ["M44 95L59 105L45 114L36 103ZM84 95L69 105L83 114L92 103Z", 1],
      ["M79 114H99V130H79Z", 2], ["M84 105H89V124H84Z", 1]],
    seams: "M85 109H88M85 114H88M85 119H88M29 122H47M27 127H45M63 107V136",
    prop: '<path d="M3 62V25H29V62ZM3 25L16 16L29 25M9 62V45H21V62M9 31H15V37H9ZM21 20L35 34H21Z"/>',
  },
  "pipekeeper-yoke": {
    label: "Pipeline Keeper / high-yoke utility vest, copper pipe closures",
    palette: ["#36534e", "#d3b168", "#cf8063"],
    panels: [["M44 95L51 97V105H77V97L84 95L96 111H32Z", 1],
      ["M32 111H55V137H25ZM96 111H73V137H103Z", 0],
      ["M35 114H50V127H35ZM78 114H93V127H78Z", 2]],
    seams: "M55 106V117H73V106M59 120V137M69 120V137M38 117H47M81 117H90M25 131H52M76 131H103",
    jewel: '<path d="M53 100V110Q64 123 75 110V100" fill="none" stroke-width="2"/><circle cx="64" cy="116" r="2"/>',
    prop: '<path d="M7 20V37H22V61H36M13 20V31H28V55H36M5 42H15M19 48H31M31 53V63"/>',
  },
  "runner-track": {
    label: "Runner / sprint track top, chevron chest, stopwatch",
    palette: ["#275478", "#e7e2c7", "#df8359"],
    panels: [["M21 109L47 94L64 108L81 94L107 109L101 117L81 103L64 117L47 103L27 117Z", 1],
      ["M47 103L64 117L81 103L86 108L64 127L42 108Z", 2],
      ["M20 117L28 117L35 137H23ZM108 117L100 117L93 137H105Z", 2]],
    seams: "M64 103V136M25 111L34 108M103 111L94 108",
    jewel: '<path d="M58 97Q64 108 70 97" fill="none"/><circle cx="64" cy="109" r="3"/><path d="M64 107V109L66 110" fill="none"/>',
    prop: '<path d="M5 65Q17 33 32 21M11 73Q25 37 39 25M18 80Q31 43 45 29M5 58L23 67"/>',
  },
  "pipeline-cyclist": {
    label: "Runner Pipelines / cycling jersey, routed piping, three-pocket hem",
    palette: ["#724e78", "#d4dfba", "#dfaa66"],
    panels: [["M21 108L44 97L51 101L37 119L19 116ZM107 108L84 97L77 101L91 119L109 116Z", 1],
      ["M48 94L53 98V103H75V98L80 94L78 108H50Z", 2],
      ["M34 123H53V137H34ZM55 123H73V137H55ZM75 123H94V137H75Z", 1]],
    seams: "M64 105V137M28 109L36 112L46 105M100 109L92 112L82 105M37 126H50M58 126H70M78 126H91",
    prop: '<path d="M6 31H21V44H33V60H45M6 37H15V50H27V66H45"/><circle cx="12" cy="74" r="7"/><circle cx="33" cy="74" r="7"/><path d="M12 74L22 60L33 74H12L18 63"/>',
  },
  "artifact-inspector": {
    label: "Runner Artifact Checks / inspection bib, sealed parcel pocket",
    palette: ["#3c4e65", "#d2b369", "#9fc1b6"],
    panels: [["M39 98L47 95L55 110H73L81 95L89 98L83 119H45Z", 1],
      ["M40 118H88L91 137H37Z", 1],
      ["M48 119L64 115L80 119V134H48Z", 0],
      ["M60 117H66V134H60Z", 2]],
    seams: "M45 105L50 115M83 105L78 115M51 124H56M71 124H77M51 129L54 131L58 126",
    prop: '<path d="M6 38L18 31L31 38L18 45ZM6 38V58L18 66L31 58V38M18 45V66M9 52L14 57L25 46"/><circle cx="112" cy="27" r="8"/><path d="M118 33L125 41"/>',
  },
  "archive-waistcoat": {
    label: "Inventory Evidence Keeper / archive waistcoat, indexed file pockets",
    palette: ["#6f3f54", "#e9dec4", "#bc9d5a"],
    panels: [["M18 137L23 108L48 94L56 100L48 137ZM110 137L105 108L80 94L72 100L80 137Z", 1],
      ["M43 95L62 111L64 116L66 111L85 95L87 137H41Z", 0],
      ["M44 118H58V132H44ZM70 118H84V132H70Z", 2],
      ["M46 114H51V124H46ZM73 112H79V124H73Z", 1]],
    seams: "M64 117V137M47 120H55M73 120H81M47 127H55M73 127H81M53 102L58 112M75 102L70 112",
    prop: '<path d="M3 27H27V42H3ZM3 44H27V59H3ZM3 61H27V76H3ZM11 32H20V36H11ZM11 49H20V53H11ZM11 66H20V70H11Z"/>',
  },
  "report-workshirt": {
    label: "Report Mechanic / rolled workshirt, document breastplate, wrench loop",
    palette: ["#b8824d", "#e9deca", "#4b6873"],
    panels: [["M18 110L28 104L40 137H23ZM110 110L100 104L88 137H105Z", 2],
      ["M48 94L57 100L52 107L40 98ZM80 94L71 100L76 107L88 98Z", 1],
      ["M31 113H51V130H31Z", 1], ["M78 113H98V126H78Z", 2]],
    seams: "M64 104V137M35 118H47M35 123H46M82 117L94 120M80 130H96M27 109L34 128M101 109L94 128",
    jewel: '<path d="M83 106L88 111L86 119L90 123L94 119L90 115L92 108L87 103Z" fill="none"/>',
    prop: '<path d="M5 24H23L30 31V62H5ZM23 24V32H30M10 39H24M10 45H24M10 51H19M10 57H22"/>',
  },
  "cartographer-mantle": {
    label: "Migration Cartographer / expedition mantle, folded chart, compass clasp",
    palette: ["#2b626b", "#d7c593", "#c68b5c"],
    panels: [["M47 94L57 99L51 137H18L23 109ZM81 94L71 99L77 137H110L105 109Z", 0],
      ["M48 94L64 102L80 94L103 107L89 120L64 107L39 120L25 107Z", 1],
      ["M73 117L96 112L99 137H76Z", 2]],
    seams: "M32 109Q40 101 47 108T61 104M68 104Q76 101 83 108T96 108M78 121L94 118M80 129L95 126M85 117L88 136",
    jewel: '<circle cx="64" cy="104" r="3"/><path d="M64 101L66 105L62 107Z" fill="none"/>',
    prop: '<path d="M3 34L13 30L23 34L33 30V63L23 67L13 63L3 67ZM13 30V63M23 34V67M7 54L13 48L19 53L28 42"/><circle cx="111" cy="22" r="7"/><path d="M111 17L114 25L108 25Z"/>',
  },
  "mesh-node-knit": {
    label: "Meshboard Maintainer / lattice knit, node fasteners, mesh shoulder drape",
    palette: ["#3e465f", "#9ebfba", "#d9b16c"],
    panels: [["M48 94L55 99V137H28L30 106ZM80 94L73 99V137H100L98 106Z", 0],
      ["M28 108L46 95L51 103L39 121L25 117Z", 1],
      ["M78 96L102 110L95 119L74 104Z", 1]],
    seams: "M36 113L49 109L43 125L53 133M49 109L52 122L43 125M78 111L90 119L78 130L91 135M90 119L95 131L78 130M59 107H69M59 117H69M59 127H69",
    jewel: '<g><circle cx="43" cy="111" r="2"/><circle cx="49" cy="121" r="2"/><circle cx="83" cy="117" r="2"/><circle cx="88" cy="129" r="2"/></g>',
    prop: '<path d="M8 27L23 40L9 58L26 72M8 27L29 24L23 40L35 57L9 58M23 40L9 58"/><circle cx="8" cy="27" r="3"/><circle cx="23" cy="40" r="3"/><circle cx="9" cy="58" r="3"/><circle cx="29" cy="24" r="3"/>',
  },
  "editor-tabard": {
    label: "Manual Editor / ivory editorial tabard, red-pencil piping",
    palette: ["#ddcfb3", "#5a526d", "#b5574a"],
    panels: [["M18 137L23 108L48 94L56 100L49 137ZM110 137L105 108L80 94L72 100L79 137Z", 1],
      ["M44 96L56 101L64 105L72 101L84 96L87 137H41Z", 0],
      ["M43 112H59V129H43Z", 2], ["M46 115H56V125H46Z", 0]],
    seams: "M64 108V136M69 112H79M69 118H79M69 124H76M47 119L49 121L54 116M44 133H84",
    jewel: '<path d="M82 100L85 101L78 117L75 119L75 115Z"/><path d="M77 114L80 115" fill="none"/>',
    prop: '<path d="M4 25H27V64H4ZM9 32H23M9 40H23M9 48H23M9 56H19"/><path d="M26 35L31 40L38 30M29 50L36 57M36 50L29 57"/>',
  },
  "builder-brick-apron": {
    label: "Meshboard Builder / masonry apron, brick pockets, square clasp",
    palette: ["#9b614d", "#d7c8a9", "#497578"],
    panels: [["M18 137L23 108L48 94L55 99L48 137ZM110 137L105 108L80 94L73 99L80 137Z", 1],
      ["M40 96L47 96L55 116H47ZM88 96L81 96L73 116H81Z", 2],
      ["M41 110H87L92 137H36Z", 0],
      ["M48 119H80V132H48Z", 2]],
    seams: "M43 115H85M39 125H48M80 125H89M53 120V126H64V132M64 120V126H75V132M52 115V118M74 115V118",
    jewel: '<path d="M58 100H70V109H58ZM61 103H67V106H61Z" fill="none"/>',
    prop: '<path d="M2 66H32V77H2ZM2 55H26V66H2ZM8 44H32V55H8ZM12 66V77M15 55V66M20 44V55"/><path d="M105 21L123 39H105ZM109 30V35H114Z"/>',
  },
  "threadscout-cowl": {
    label: "Thread Scout / trail cowl, woven scout vest, spool clasp",
    palette: ["#67704c", "#d6c6a3", "#bb805d"],
    panels: [["M43 95L57 101L61 137H27L33 105ZM85 95L71 101L67 137H101L95 105Z", 0],
      ["M41 96Q64 113 87 96L82 111L64 116L46 110Z", 1],
      ["M58 110L65 115L53 137H44Z", 1],
      ["M79 117H93V132H79Z", 2]],
    seams: "M45 102Q64 117 83 102M50 113L60 119M81 121H91M81 126H89M34 114L39 136",
    jewel: '<path d="M67 109H73V118H67ZM65 109H75M65 118H75M68 112H72M68 115H72" fill="none"/>',
    prop: '<circle cx="17" cy="31" r="10"/><path d="M24 39L34 52M8 63Q18 49 24 61T8 77M101 24H119V31H101ZM105 31V51H115V31M101 51H119V58H101Z"/>',
  },
  "pixel-blocks": {
    label: "Pixel / stepped color-block vest, square enamel pixels",
    palette: ["#495478", "#cc876f", "#a7c7b1"],
    panels: [["M18 137V110H27V102H45V95H53V107H45V137Z", 0],
      ["M110 137V110H101V102H83V95H75V107H83V137Z", 1],
      ["M45 107H59V118H70V129H83V137H45Z", 2],
      ["M75 107H67V115H59V123H51V131H59V123H67V115H75Z", 1]],
    seams: "M23 116H32V124H40M89 111V119H99M51 110H56M72 131H79",
    jewel: '<path d="M59 99H64V104H69V109H64V104H59Z"/>',
    prop: '<path d="M4 20H13V29H4ZM13 29H22V38H13ZM4 38H13V47H4ZM22 20H31V29H22ZM22 47H31V56H22ZM101 63H110V72H101ZM110 72H119V81H110Z"/>',
  },
  "cassette-deck": {
    label: "Tape Curator / cassette-pocket jacket, tape-loop scarf",
    palette: ["#805446", "#d4b68b", "#89aeb2"],
    panels: [["M46 94L55 100L51 137H18L23 108ZM82 94L73 100L77 137H110L105 108Z", 0],
      ["M49 95Q64 107 79 95L77 103Q64 115 51 103L56 137H48Z", 2],
      ["M71 113H98V131H71Z", 1], ["M75 117H94V125H75Z", 0]],
    seams: "M79 118V123M90 118V123M81 121H88M77 128H92M29 116L43 112M27 120L41 116",
    prop: '<path d="M4 27H32V48H4ZM8 31H28V40H8ZM10 44H26"/><circle cx="12" cy="35" r="3"/><circle cx="24" cy="35" r="3"/><path d="M10 48Q0 68 20 65T30 80"/>',
  },
  "rig-cable-harness": {
    label: "Rig Evidence Keeper / padded harness, cable loops, jointed rig",
    palette: ["#384556", "#d2d2bd", "#d89462"],
    panels: [["M48 94Q64 104 80 94L85 137H43Z", 1],
      ["M38 98L46 96L57 137H45ZM90 98L82 96L71 137H83Z", 0],
      ["M42 111H86V118H42Z", 2],
      ["M52 121H76V134H52Z", 0]],
    seams: "M41 104L50 133M87 104L78 133M46 114H54M74 114H82M56 125H72M56 129H67",
    jewel: '<path d="M33 112Q20 123 38 129Q50 133 43 118M92 112Q109 122 91 130" fill="none" stroke-width="1.4"/>',
    prop: '<circle cx="14" cy="24" r="5"/><circle cx="23" cy="43" r="4"/><circle cx="10" cy="62" r="4"/><path d="M14 29L23 39M21 47L11 58M10 66V80M10 73L3 81M10 73L19 81M23 43L35 47"/>',
  },
  "trickroom-harlequin": {
    label: "TrickRoom Continuity / harlequin waistcoat, looping continuity cord",
    palette: ["#624571", "#d1b276", "#b4cab7"],
    panels: [["M18 137L23 108L48 94L56 100L49 137ZM110 137L105 108L80 94L72 100L79 137Z", 2],
      ["M44 95L64 108L84 95L87 137H41Z", 0],
      ["M49 108L57 116L49 124L41 116ZM65 108L73 116L65 124L57 116ZM81 108L89 116L81 124L73 116ZM57 124L65 132L57 140L49 132ZM73 124L81 132L73 140L65 132Z", 1]],
    seams: "M49 95L59 105M79 95L69 105M64 111V136",
    jewel: '<path d="M36 109C24 96 24 125 36 113C48 101 48 126 36 113" fill="none"/>',
    prop: '<path d="M4 77V22H27V77M9 77V29H22V77M22 29L34 37V72L22 77M27 21L35 13L38 19L31 25"/><circle cx="29" cy="55" r="1.5"/>',
  },
  "camera-safari": {
    label: "TrickRoom Camera / safari shooting vest, rangefinder pendant",
    palette: ["#88754f", "#e0d6b7", "#557a79"],
    panels: [["M18 137L23 108L48 94L55 100L48 137ZM110 137L105 108L80 94L73 100L80 137Z", 1],
      ["M42 96L54 101L57 137H29L34 105ZM86 96L74 101L71 137H99L94 105Z", 0],
      ["M31 111H48V122H31ZM80 111H97V122H80ZM31 125H48V136H31ZM80 125H97V136H80Z", 2]],
    seams: "M33 114H46M82 114H95M33 128H46M82 128H95",
    jewel: '<path d="M52 97L57 119M76 97L71 119" fill="none"/><path d="M55 117H73V129H55ZM58 114H64V117H58Z"/><circle cx="65" cy="123" r="3" fill="none"/>',
    prop: '<path d="M3 28H28V45H3ZM28 33L38 28V45L28 40M15 45V64M15 55L4 78M15 55L28 78"/><circle cx="15" cy="36" r="5"/>',
  },
  "windowpane-coat": {
    label: "WindowPane / glazed-check coat, four-pane clasp",
    palette: ["#467078", "#c7d7c1", "#e1b779"],
    panels: [["M48 94L57 100L54 137H17L23 108ZM80 94L71 100L74 137H111L105 108Z", 0],
      ["M44 96L56 103L51 112L37 102ZM84 96L72 103L77 112L91 102Z", 1],
      ["M52 113H76V137H52Z", 1]],
    seams: "M27 108V136M38 112V136M49 115V136M79 115V136M90 112V136M101 108V136M22 117H51M20 128H51M77 117H106M77 128H108M64 114V137M53 125H75",
    jewel: '<path d="M58 101H70V111H58ZM64 101V111M58 106H70" fill="none"/>',
    prop: '<path d="M4 20H30V66H4ZM17 20V66M4 43H30M1 69H34M7 23H14V39H7ZM20 47H27V62H20Z"/>',
  },
  "desk-daywear": {
    label: "WorkDesk / rolled sleeves, asymmetric sweater vest, desk-pocket pen",
    palette: ["#9b674d", "#e7d7b8", "#506778"],
    panels: [["M18 137L23 108L48 94L55 100L48 137ZM110 137L105 108L80 94L73 100L80 137Z", 1],
      ["M44 95L64 111L82 95L86 137H40Z", 0],
      ["M48 95L64 107L73 99L76 104L64 117L45 103Z", 2],
      ["M76 117H90V130H76Z", 2]],
    seams: "M23 112L32 130M105 112L96 130M24 122L31 120M104 122L97 120M44 133H83M79 120H87",
    jewel: '<path d="M81 111V124M85 110V123" fill="none" stroke-width="1.3"/>',
    prop: '<path d="M1 69H35V75H1ZM7 75V87M29 75V87M5 57H21V68H5ZM21 59Q29 57 27 64H21M99 24H123V42H99ZM110 42V49M104 49H117"/>',
  },
});

function avatarPortraitDirection(persona) {
  const direction = Object.hasOwn(avatarPortraitArtDirections, persona.personaId)
    ? avatarPortraitArtDirections[persona.personaId]
    : Object.hasOwn(avatarContextArtDirections, persona.contextId) ? avatarContextArtDirections[persona.contextId] : {};
  return persona.avatarPresentation === undefined ? direction : { ...direction, presentation: persona.avatarPresentation };
}

function personaAvatarDataUri(persona) {
  return avatarStudyDataUri(persona.profileImageData, 9, persona, avatarPortraitDirection(persona));
}

function avatarEarlyStudyDataUri(seed, version) {
  const recipe = avatarRecipe(seed);
  if (![3, 4, 5].includes(version)) throw new RangeError("Unknown avatar study version");
  const { background, skin, hair, shirt, hairStyle, eyeStyle, mouthStyle, accessory,
    faceWidth, faceHeight, eyeSpacing, eyeColor, eyebrowTilt } = recipe;
  const flat = version === 3;
  const natural = version >= 5;
  const mix = (left, right, amount) => `#${[1, 3, 5].map(offset =>
    Math.round(parseInt(left.slice(offset, offset + 2), 16) * (1 - amount) +
      parseInt(right.slice(offset, offset + 2), 16) * amount).toString(16).padStart(2, "0")).join("")}`;
  const shade = (color, amount) => mix(color, amount < 0 ? "#211b29" : "#fff3dc", Math.abs(amount));
  const ink = shade(hair, -.65);
  const skinDark = mix(skin, "#643b38", .43);
  const skinDeep = mix(skin, "#39262e", .62);
  const lip = mix(skin, "#9a4e52", .38);
  let detail = 2166136261;
  for (const character of `portrait-detail:${seed.toLowerCase()}`) {
    detail = Math.imul(detail ^ character.charCodeAt(0), 16777619) >>> 0;
  }
  const unit = shift => ((detail >>> shift) & 31) / 31;
  const w = faceWidth - (natural ? .8 : 0);
  const chin = 61 + faceHeight;
  const jaw = natural ? 16 + unit(3) * 3 : 18.5;
  const head = `M${64 - w} 52C${63 - w} 34 47 ${61 - faceHeight} 64 ${61 - faceHeight}
    C81 ${61 - faceHeight} ${65 + w} 34 ${64 + w} 52
    C${65 + w} 64 ${62 + w} 77 ${64 + jaw} 85
    Q75 ${chin} 64 ${chin + 1}Q53 ${chin} ${64 - jaw} 85
    C${66 - w} 77 ${63 - w} 64 ${64 - w} 52Z`;
  const backHair = [
    "",
    "",
    '<path d="M32 43C21 53 24 83 33 97L46 90H82L96 98C107 85 105 53 96 42Z"/>',
    '<path d="M31 51C21 5 107 6 98 54L100 99Q88 107 77 95H50Q36 107 27 99Z"/>',
    '<path d="M30 49C20 9 109 4 99 58L105 119L83 116L76 91H50L43 116L22 119Z"/>',
    "",
    '<path d="M75 26C65 13 77 5 89 8C105 9 105 29 92 33Z"/>',
    "",
  ][hairStyle];
  const frontHair = [
    '<path d="M32 53L32 39C31 20 47 15 63 17C86 13 98 28 96 45L93 55L85 39Q75 44 66 37Q54 31 44 39L38 55Z"/>',
    '<path d="M32 55C23 37 29 24 43 20C63 10 92 12 97 32L95 55L86 46L83 32C74 45 53 48 39 44L38 56Z"/>',
    '<path d="M31 52C23 46 26 34 31 32C24 22 35 15 44 18C47 8 62 10 66 16C73 9 88 15 89 23C101 23 105 38 98 43L96 55L86 44C81 48 76 41 74 37C65 45 57 39 55 35C49 43 42 39 39 43L38 56Z"/>',
    '<path d="M31 61V38C31 9 99 10 98 43L94 66L85 43L78 34C66 43 51 44 40 39L38 63Z"/>',
    '<path d="M30 61C22 23 45 13 59 16C83 9 103 26 98 46L93 68L83 37C72 44 56 48 42 40L37 67Z"/>',
    '<path d="M31 54C30 43 27 34 32 29L42 34L45 18L57 26C62 20 67 15 71 14L77 27L90 22L91 36L100 37L95 56L84 42L69 39L51 34L39 45Z"/>',
    '<path d="M32 56C26 24 40 17 61 19C84 13 101 27 97 50L90 58L82 36C69 43 53 42 42 36L38 57Z"/>',
    '<path d="M34 52Q29 44 35 36L41 43L39 57ZM89 43L95 36Q101 44 94 54L89 57Z"/>',
  ][hairStyle];
  const strandPaths = [
    "M35 39C39 23 62 21 79 25M42 38Q52 29 61 34M65 28Q79 38 90 32M88 36L92 46",
    "M33 39C28 25 51 18 63 21M39 39C56 43 74 30 82 25M42 43C57 47 77 36 85 29M89 28Q94 35 93 45",
    "M29 36C29 27 40 28 40 35M33 24C36 17 47 22 44 29M49 18C57 12 63 20 59 25M68 20C75 13 83 23 78 28M88 30Q98 25 98 36M87 40Q95 37 97 46",
    "M35 40C32 20 63 18 79 23M41 35Q61 41 79 29M85 35Q92 45 93 55M35 58L34 89M95 67L96 93",
    "M34 41C30 24 51 19 67 21M42 36Q63 43 82 29M87 37Q94 49 92 59M35 66C30 82 32 99 28 111M93 70Q96 95 99 110",
    "M34 38L41 41M47 25Q47 31 53 33M62 31L69 20L73 31M81 33L87 29L86 38M92 42L96 41",
    "M36 39C33 24 53 20 69 23M43 35Q65 40 82 28M48 38Q67 42 83 33M89 34Q94 41 93 48",
    "M35 43L37 48M94 42L92 48",
  ][hairStyle];
  const eyeY = natural ? 59.5 : 60;
  const eyeW = natural ? 6.1 : 6.4;
  const opening = eyeStyle === 1 ? (natural ? 2.8 : 3.2) : (natural ? 2.1 : 2.5);
  const eyeMarkup = [];
  const eyeClips = [];
  for (const [index, x] of [64 - eyeSpacing, 64 + eyeSpacing].entries()) {
    const side = index ? 1 : -1;
    if (eyeStyle === 2 || (eyeStyle === 3 && index === 1)) {
      eyeMarkup.push(`<g data-eye="closed"><path d="M${x - eyeW} ${eyeY}Q${x} ${eyeY + 3.5} ${x + eyeW} ${eyeY - .1}" fill="none" stroke="${ink}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M${x - 4.5} ${eyeY + 2.5}Q${x} ${eyeY + 4.5} ${x + 4.5} ${eyeY + 2.7}" fill="none" stroke="${skinDark}" stroke-width=".6" opacity=".55"/></g>`);
      continue;
    }
    const contour = `M${x - eyeW} ${eyeY}C${x - 3.6} ${eyeY - opening - 1} ${x + 2.5} ${eyeY - opening - .7} ${x + eyeW} ${eyeY - .2}
      C${x + 2.7} ${eyeY + opening} ${x - 2.8} ${eyeY + opening} ${x - eyeW} ${eyeY}Z`;
    eyeClips.push(`<clipPath id="eye-${index}"><path d="${contour}"/></clipPath>`);
    const irisX = x + (unit(12) - .5) * .8;
    eyeMarkup.push(`<g data-eye="open">
      <path d="${contour}" fill="${flat ? "#f5eee4" : "url(#sclera)"}"/>
      <g clip-path="url(#eye-${index})">
        <circle cx="${irisX}" cy="${eyeY - .1}" r="${natural ? 2.65 : 2.8}" fill="${flat ? eyeColor : "url(#iris)"}" stroke="${shade(eyeColor, -.5)}" stroke-width=".45"/>
        <circle cx="${irisX}" cy="${eyeY - .15}" r="1.25" fill="${ink}"/>
        <circle cx="${irisX - .65}" cy="${eyeY - .9}" r=".43" fill="#fff9ee" opacity=".9"/>
        ${flat ? "" : `<path d="M${x - eyeW} ${eyeY - 1}Q${x} ${eyeY - opening - 1} ${x + eyeW} ${eyeY - 1}" fill="none" stroke="${skinDeep}" stroke-width="1.7" opacity=".25"/>`}
      </g>
      <path d="M${x - eyeW} ${eyeY}C${x - 3.6} ${eyeY - opening - 1} ${x + 2.5} ${eyeY - opening - .7} ${x + eyeW} ${eyeY - .2}" fill="none" stroke="${ink}" stroke-width="${natural ? 1.15 : 1.5}" stroke-linecap="round"/>
      <path d="M${x - eyeW + 1} ${eyeY + .5}Q${x} ${eyeY + opening + .8} ${x + eyeW - 1} ${eyeY + .2}" fill="none" stroke="${skinDark}" stroke-width=".65" opacity=".7"/>
      ${natural ? `<path d="M${x - 5.3} ${eyeY - opening - 2.3}Q${x + side} ${eyeY - opening - 3.8} ${x + 5.5} ${eyeY - opening - 1.8}" fill="none" stroke="${skinDark}" stroke-width=".6" opacity=".55"/>` : ""}
    </g>`);
  }
  const brows = [64 - eyeSpacing, 64 + eyeSpacing].map((x, index) => {
    const lift = index ? eyebrowTilt * 1.2 : 0;
    return `<path d="M${x - 6.7} ${51 + lift}Q${x - 1} ${47.8 + lift} ${x + 6.4} ${50.8 - lift}
      L${x + 5.5} ${52 - lift}Q${x} ${50.3 + lift} ${x - 6.7} ${52.2 + lift}Z"/>`;
  }).join("");
  const mouths = [
    `<path d="M55.5 81.5Q64 85.7 73 81" fill="none" stroke="${lip}" stroke-width="1.4" stroke-linecap="round"/><path d="M59 85Q64 86.8 69 84.9" fill="none" stroke="${shade(skin, .28)}" stroke-width=".8"/>`,
    `<path d="M53.5 80Q64 84 74.5 79.6C73 91 55 92 53.5 80Z" fill="${skinDeep}"/><path d="M55 81Q64 84 73 80.7L71.5 83.3Q64 85.1 56.3 83.6Z" fill="#eee7da"/><path d="M59 87Q64 85 69 87Q64 89.5 59 87" fill="${lip}"/>`,
    `<path d="M58 81Q64 78.9 70 81.2Q68 87.6 64 87.5Q60 87 58 81Z" fill="${skinDeep}"/><path d="M60 86Q64 83.9 68 86" fill="none" stroke="${lip}" stroke-width="1.3"/><path d="M59 80Q64 78.5 69 80" fill="none" stroke="${lip}" stroke-width=".8"/>`,
    `<path d="M56 82.4Q64 85.1 73 79.7" fill="none" stroke="${lip}" stroke-width="1.4" stroke-linecap="round"/><path d="M71.7 79L74 79.3" stroke="${skinDark}" stroke-width=".65"/>`,
    `<path d="M57 82Q61 79.6 64 81Q67 79.8 71 82Q65 85.2 57 82Z" fill="${lip}" opacity=".72"/><path d="M57.5 82Q64 83.1 70.5 82" fill="none" stroke="${skinDeep}" stroke-width=".75"/>`,
  ];
  const earX = [64 - w - 1.8, 64 + w + 1.8];
  const earrings = earX.map((x, index) => `<g data-earring="${index ? "right" : "left"}">
    <ellipse cx="${x}" cy="73.5" rx="2.6" ry="3" fill="${flat ? "#d9ad54" : "url(#gold)"}" stroke="#896034" stroke-width=".65"/>
    <circle cx="${x - .6}" cy="72.4" r=".65" fill="#fff3c2"/>
  </g>`).join("");
  const glasses = accessory === 1 ? [64 - eyeSpacing, 64 + eyeSpacing].map(x =>
    `<ellipse cx="${x}" cy="${eyeY + .1}" rx="9" ry="7.5"/>`).join("") :
    [64 - eyeSpacing, 64 + eyeSpacing].map(x =>
      `<rect x="${x - 9}" y="${eyeY - 6.1}" width="18" height="13.2" rx="3.1"/>`).join("");
  const accessories = [
    "",
    `<g fill="#e1efff" fill-opacity=".06" stroke="${ink}" stroke-width="1.6">${glasses}<path d="M${73 - eyeSpacing} ${eyeY - .7}Q64 ${eyeY - 4} ${55 + eyeSpacing} ${eyeY - .7}M${64 - w - 2} 57L${55 - eyeSpacing} 58M${73 + eyeSpacing} 58L${66 + w} 57" fill="none"/></g>`,
    `<g fill="#e1efff" fill-opacity=".06" stroke="${ink}" stroke-width="1.8">${glasses}<path d="M${73 - eyeSpacing} ${eyeY - 1}H${55 + eyeSpacing}M${64 - w - 2} 56L${55 - eyeSpacing} 57M${73 + eyeSpacing} 57L${66 + w} 56" fill="none"/></g>`,
    earrings,
    `<g fill="${skinDark}" opacity=".65">${[[44,70],[48,69],[51,72],[77,72],[80,69],[84,70]].map(([x,y]) =>
      `<circle cx="${x}" cy="${y}" r=".8"/>`).join("")}</g>`,
  ];
  const outline = flat ? `stroke="${ink}" stroke-width="1.1"` : natural ? 'stroke="none"' :
    `stroke="${shade(skin, -.48)}" stroke-width=".7"`;
  const fill = (id, color) => flat ? color : `url(#${id})`;
  const definitions = `
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${shade(background, .13)}"/><stop offset="1" stop-color="${shade(background, -.15)}"/></linearGradient>
    <radialGradient id="skin" cx=".28" cy=".28" r=".85"><stop stop-color="${shade(skin, .2)}"/><stop offset=".48" stop-color="${skin}"/><stop offset=".82" stop-color="${shade(skin, -.14)}"/><stop offset="1" stop-color="${shade(skin, -.32)}"/></radialGradient>
    <linearGradient id="hair" x1=".15" y1="0" x2=".85" y2="1"><stop stop-color="${shade(hair, .23)}"/><stop offset=".4" stop-color="${hair}"/><stop offset="1" stop-color="${shade(hair, -.48)}"/></linearGradient>
    <linearGradient id="rear" x2="1" y2=".6"><stop stop-color="${shade(hair, -.08)}"/><stop offset="1" stop-color="${shade(hair, -.55)}"/></linearGradient>
    <linearGradient id="shirt" x1=".1" y1="0" x2=".85" y2="1"><stop stop-color="${shade(shirt, .18)}"/><stop offset=".45" stop-color="${shirt}"/><stop offset="1" stop-color="${shade(shirt, -.38)}"/></linearGradient>
    <linearGradient id="sclera" x2=".1" y2="1"><stop stop-color="#c5bbae"/><stop offset=".4" stop-color="#f2eade"/><stop offset="1" stop-color="#ded7cb"/></linearGradient>
    <radialGradient id="iris" cx=".4" cy=".5"><stop stop-color="${shade(eyeColor, .18)}"/><stop offset=".65" stop-color="${eyeColor}"/><stop offset="1" stop-color="${shade(eyeColor, -.6)}"/></radialGradient>
    <linearGradient id="gold" x2="1" y2=".65"><stop stop-color="#fff0b2"/><stop offset=".35" stop-color="#dbb25a"/><stop offset=".6" stop-color="#b07c31"/><stop offset=".85" stop-color="#f6d881"/><stop offset="1" stop-color="#94672c"/></linearGradient>
    <radialGradient id="cheek"><stop stop-color="#c56860" stop-opacity=".24"/><stop offset="1" stop-color="#c56860" stop-opacity="0"/></radialGradient>
    <radialGradient id="light"><stop stop-color="${shade(skin, .45)}" stop-opacity=".55"/><stop offset="1" stop-color="${shade(skin, .45)}" stop-opacity="0"/></radialGradient>
    <linearGradient id="plane" x2="1" y2=".3"><stop stop-color="${skinDark}" stop-opacity="0"/><stop offset="1" stop-color="${skinDark}" stop-opacity=".45"/></linearGradient>
    <filter id="soft" x="-.35" y="-.35" width="1.7" height="1.7"><feGaussianBlur stdDeviation=".9"/></filter>
    <clipPath id="tile"><rect width="128" height="128" rx="18"/></clipPath>
    <clipPath id="head"><path d="${head}"/></clipPath>
    <clipPath id="hair-shape">${frontHair}</clipPath>
    ${eyeClips.join("")}`;
  const facePlanes = flat ? "" : `<g clip-path="url(#head)">
    <path d="M${64 + w - 5} 40Q84 65 78 79L67 ${chin + 3}H107V34Z" fill="url(#plane)"/>
    <ellipse cx="46" cy="72" rx="11" ry="7" fill="url(#cheek)"/>
    <ellipse cx="82" cy="72" rx="10" ry="7" fill="url(#cheek)"/>
    <ellipse cx="53" cy="43" rx="17" ry="18" fill="url(#light)"/>
    <path d="M34 45Q64 35 93 43L91 49Q63 44 35 51Z" fill="${skinDeep}" opacity=".12" filter="url(#soft)"/>
    ${natural ? `<path d="M49 65Q52 70 55 72M76 65Q74 69 73 72" fill="none" stroke="${skinDark}" stroke-width="1.3" opacity=".16" filter="url(#soft)"/>
      <ellipse cx="61" cy="91" rx="8" ry="2.2" fill="url(#light)"/>
      <path d="M65 56Q69 64 70 72L65 75L60 72Q64 67 65 56Z" fill="url(#plane)"/>
      <path d="M63 59L62.5 69Q61 72 63 73" fill="none" stroke="${shade(skin, .34)}" stroke-width="1" opacity=".8"/>
      <path d="M59.8 74Q64 77.3 69 73.5" fill="none" stroke="${skinDark}" stroke-width=".7" opacity=".6"/>
      <path d="M61 77L60.6 79M66.3 77L67.2 79" stroke="${skinDark}" stroke-width=".55" opacity=".45"/>` : ""}
  </g>`;
  const hairDetail = flat ? "" : `<g clip-path="url(#hair-shape)" fill="none" stroke-linecap="round">
    <path d="${strandPaths}" stroke="${shade(hair, .38)}" stroke-width="1.25" opacity=".64"/>
    <path d="${strandPaths}" stroke="${shade(hair, -.48)}" stroke-width=".65" opacity=".45" transform="translate(1.7 2.2)"/>
    <path d="${strandPaths}" stroke="${shade(hair, .55)}" stroke-width=".45" opacity=".6" transform="translate(-.6 -.7)"/>
  </g>`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128" data-avatar-version="study-v${version}">
    <defs>${definitions}</defs>
    <g clip-path="url(#tile)">
      <rect width="128" height="128" fill="${fill("background", background)}"/>
      <ellipse cx="40" cy="46" rx="57" ry="65" fill="#fff3df" opacity="${flat ? ".12" : ".18"}"/>
      <g data-feature="hair-back" fill="${fill("rear", shade(hair, -.25))}">${backHair}</g>
      ${hairStyle === 6 && !flat ? `<path d="M78 24C70 13 91 7 96 18C100 30 82 32 81 21C80 15 91 14 92 21" fill="none" stroke="${shade(hair, .4)}" stroke-width="1.2" opacity=".8"/>` : ""}
      <path d="M17 130L20 118Q23 106 48 100L56 97H72L80 100Q105 105 108 118L111 130Z" fill="${fill("shirt", shirt)}"/>
      <path d="M55 86H73V101Q64 108 55 101Z" fill="${fill("skin", skin)}"/>
      <path d="M55 88Q64 98 73 88V96Q64 103 55 96Z" fill="${skinDark}" opacity=".6"/>
      <path d="M49 100L58 108L64 105L70 108L79 100L86 104L76 115L64 108L52 115L42 104Z" fill="${shade(shirt, -.24)}"/>
      <path d="M49 100L58 108M79 100L70 108" fill="none" stroke="${shade(shirt, .38)}" stroke-width="1.2"/>
      ${!flat ? `<path d="M25 125Q26 113 40 110M99 129Q100 117 89 113" fill="none" stroke="${shade(shirt, .35)}" stroke-width="1.4" opacity=".45"/><path d="M39 128L41 117M89 128L87 117" stroke="${shade(shirt, -.38)}" opacity=".55"/>` : ""}
      <g data-feature="ears" fill="${fill("skin", skin)}" ${outline}>${earX.map(x =>
        `<ellipse cx="${x}" cy="63.5" rx="4.3" ry="8.5"/>`).join("")}</g>
      <g fill="none" stroke="${skinDark}" stroke-width=".85">${earX.map(x =>
        `<path d="M${x - 1} 60Q${x + 2.5} 57 ${x + 1.5} 64L${x} 68"/>`).join("")}</g>
      <path data-feature="head" d="${head}" fill="${fill("skin", skin)}" ${outline}/>
      ${facePlanes}
      <g data-feature="hair" fill="${fill("hair", hair)}">${frontHair}</g>
      ${hairDetail}
      <g data-feature="eyebrows" fill="${shade(hair, -.35)}">${brows}</g>
      <g data-feature="eyes">${eyeMarkup.join("")}</g>
      ${natural ? "" : `<path d="M64 65L61 73Q64 75 67 73" fill="none" stroke="${skinDark}" stroke-width="1" stroke-linecap="round"/>`}
      <g data-feature="mouth">${mouths[mouthStyle]}</g>
      <g data-feature="accessory">${accessories[accessory]}</g>
    </g>
  </svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

function avatarWardrobeProfile(seed, persona = {}, appearance = {}) {
  avatarRecipe(seed);
  if (!persona || typeof persona !== "object" || Array.isArray(persona) ||
      !appearance || typeof appearance !== "object" || Array.isArray(appearance)) {
    throw new TypeError("Portrait metadata and art direction must be objects");
  }
  const presentations = ["feminine", "masculine", "androgynous"];
  if (appearance.presentation !== undefined && !presentations.includes(appearance.presentation)) {
    throw new TypeError("Unknown fictional clothing presentation");
  }
  if (appearance.flair !== undefined && !["restrained", "bold"].includes(appearance.flair)) {
    throw new TypeError("Unknown professional wardrobe flair");
  }
  if (appearance.expression !== undefined && !["open", "friendly-wink", "kiss-wink"].includes(appearance.expression)) {
    throw new TypeError("Unknown authored portrait expression");
  }
  if (appearance.facialHair !== undefined &&
      !["none", "stubble", "goatee", "boxed-beard", "chevron", "handlebar", "full-beard"].includes(appearance.facialHair)) {
    throw new TypeError("Unknown authored facial-hair style");
  }
  if (appearance.theme !== undefined && !["role", "goth", "butler", "pam"].includes(appearance.theme)) {
    throw new TypeError("Unknown portrait art direction");
  }
  const outfits = ["role", "cable-knit", "mandarin", "suspenders", "chore-jacket", "map-shirt",
    "mockneck-drape", "linen-wrap", "tweed-cravat", "zip-hoodie", "bib-overalls", "shawl-cardigan",
    "embroidered-smock", "moto-jacket", "satin-bomber", "breton-sling", "cardboard-harness",
    ...Object.keys(avatarNamedOutfits)];
  if (appearance.outfit !== undefined && !outfits.includes(appearance.outfit)) {
    throw new TypeError("Unknown individual portrait outfit");
  }
  if (["goth", "butler", "pam"].includes(appearance.theme) && appearance.outfit !== undefined && appearance.outfit !== "role") {
    throw new TypeError("Themed art direction already supplies its own outfit");
  }
  let state = 2166136261;
  for (const c of `wardrobe:${seed.toLowerCase()}`) state = Math.imul(state ^ c.charCodeAt(0), 16777619) >>> 0;
  const role = [persona.displayName, persona.persona].filter(value => typeof value === "string").join(" ").toLowerCase();
  const family = /comedy|goblin/.test(role) ? "creative" :
    /research|scout/.test(role) ? "research" :
    /daily.ops|workdesk/.test(role) ? "operations" :
    /skills?.library|maintainer|meshboard/.test(role) ? "architect" :
    /migration|inventory|resource.report/.test(role) ? "analyst" :
    /vtub|camera|motion|rig |kardboard|trickroom/.test(role) ? "maker" : "general";
  const stats = persona.personalityStats ?? {};
  if (typeof stats !== "object" || Array.isArray(stats)) {
    throw new TypeError("Wardrobe characteristics must be an object");
  }
  const score = name => {
    const value = stats[name];
    if (value !== undefined && (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 100)) {
      throw new TypeError(`Invalid wardrobe characteristic: ${name}`);
    }
    return value;
  };
  return {
    family,
    expression: appearance.expression || "open",
    facialHair: appearance.facialHair || "none",
    theme: appearance.theme || "role",
    outfit: appearance.outfit || "role",
    presentation: appearance.presentation || presentations[state % presentations.length],
    flair: appearance.flair || (family === "creative" ? "bold" : "restrained"),
    structured: score("seriousness") >= 70,
    accent: score("humor") >= 65,
    emblem: score("curiosity") >= 70,
    topstitch: score("persistence") >= 70,
    softLayer: score("helpfulness") >= 70,
  };
}

function avatarNeckMarkup(skin, mix) {
  return `<g data-feature="neck-anatomy">
    <path data-feature="neck" d="M55 80H73V91Q73 95 79 97L75 102Q64 105 53 102L49 97Q55 95 55 91Z" fill="url(#neck)" stroke="${mix(skin, "#38292c", .3)}" stroke-width=".5"/>
    <path d="M59 89Q59 94 56 97M69 89Q69 94 72 97" fill="none" stroke="${mix(skin, "#654747", .25)}" stroke-width=".45" opacity=".45"/>
  </g>`;
}

function avatarWardrobeMarkup(style, shirt, skin, mix) {
  if (style.theme === "goth") return avatarGothWardrobeMarkup(style, skin, mix);
  if (style.theme === "butler") return avatarButlerWardrobeMarkup(skin, mix);
  if (style.theme === "pam") return avatarPamWardrobeMarkup(style, skin, mix);
  if (Object.hasOwn(avatarNamedOutfits, style.outfit)) return avatarNamedWardrobeMarkup(style, skin, mix);
  if (style.outfit !== "role") return avatarIndividualWardrobeMarkup(style, skin, mix);
  const feminine = style.presentation === "feminine";
  const masculine = style.presentation === "masculine";
  const edge = mix(shirt, "#202735", .55);
  const pale = mix(shirt, "#fff0d6", style.softLayer ? .8 : .58);
  const accent = mix(shirt, style.accent ? "#e5aa66" : "#c5d5da", .65);
  const waist = feminine ? 34 : masculine ? 25 : 30;
  const shoulder = feminine ? 20 : masculine ? 14 : 17;
  const neckline = feminine ?
    (style.flair === "bold" ? "L53 91L64 103L75 91" : "L53 91Q64 102 75 91") :
    masculine ? "L53 91L58 96H70L75 91" : "L53 91Q64 99 75 91";
  const body = `M${shoulder - 3} 135L${shoulder} 110Q${shoulder + 3} 99 48 92${neckline}L80 92Q${125 - shoulder} 99 ${128 - shoulder} 110L${131 - shoulder} 135Z`;
  const lapel = feminine ? (style.structured ?
    "Q52 99 56 105L52 109L61 128Q47 117 41 99Z" :
    "Q54 103 55 108L61 128Q45 115 41 99Z") :
    style.structured ? "L55 103L49 109L61 128L49 119L41 99Z" :
    "Q55 101 57 105L61 128Q47 115 41 99Z";
  let garment;
  if (style.family === "analyst") {
    garment = `<path d="${feminine ? "M46 94Q53 104 61 108L64 112L67 108Q75 104 82 94L79 115L85 135H43L49 115Z" :
      "M46 94L57 106L64 110L71 106L82 94L85 135H43Z"}" fill="${edge}"/>
      <path d="M49 94L60 108M79 94L68 108M64 111V135" fill="none" stroke="${accent}" stroke-width=".7"/>
      ${[115,123,131].map(y => `<circle cx="64" cy="${y}" r=".8" fill="url(#gold)"/>`).join("")}`;
  } else if (style.family === "maker") {
    garment = `<path d="M46 93L53 96L55 135H35L37 108ZM82 93L75 96L73 135H93L91 108Z" fill="url(#shirt)"/>
      <path d="M53 97L55 135M75 97L73 135M37 106L48 109M91 106L80 109" fill="none" stroke="${accent}" stroke-width=".9"/>
      <path d="M38 113H49V122H38Z" fill="${edge}" opacity=".55"/><path d="M39 115H48" stroke="${accent}" stroke-width=".7"/>`;
  } else if (style.family === "research") {
    garment = `<path d="M46 93L53 95L56 135H34L38 105ZM82 93L75 95L72 135H94L90 105Z" fill="${edge}"/>
      <path d="M45 95Q54 106 64 106Q74 106 83 95L78 111Q66 116 52 108L49 121L43 118L48 106Z" fill="${accent}"/>
      <path d="M45 101Q62 115 80 103M47 109L46 118" fill="none" stroke="${pale}" stroke-width=".6" opacity=".7"/>`;
  } else {
    garment = `<path d="M46 93${lapel}" fill="${mix(shirt, "#fff0d6", .12)}" stroke="${edge}" stroke-width=".55"/>
      <path d="M46 93${lapel}" transform="translate(128 0) scale(-1 1)" fill="${mix(shirt, "#172335", .13)}" stroke="${edge}" stroke-width=".55"/>`;
    if (style.family === "creative") {
      garment += `<path d="M45 96L58 108L51 111L61 128L48 117L39 100Z" fill="${edge}"/>
        <path d="M45 97L55 107L50 110" fill="none" stroke="${accent}" stroke-width="1.6"/>
        <path d="M82 112L88 110L86 116L91 119L84 119L81 125L80 118L75 116Z" fill="${accent}"/>`;
    } else if (style.family === "operations") {
      garment += feminine ?
        `<path d="M52 99Q64 111 78 102L72 112L54 135H43L62 113Q55 109 52 99Z" fill="${mix(pale, shirt, .17)}"/>
        <path d="M53 101Q62 111 75 104M72 111L53 134" fill="none" stroke="${accent}" stroke-width=".65"/>` :
        `<path d="M54 102L70 108L60 119L72 135H52L58 119Z" fill="${mix(pale, shirt, .17)}"/>
        <path d="M55 103L69 108L59 119L70 134" fill="none" stroke="${accent}" stroke-width=".65"/>`;
    } else if (style.family === "architect") {
      garment += `<path d="M53 121L75 131M56 123L53 135" fill="none" stroke="${edge}" stroke-width=".7"/>
        <circle cx="54" cy="127" r="1" fill="url(#gold)"/><circle cx="73" cy="127" r="1" fill="url(#gold)"/>`;
    }
  }
  const motif = style.family === "research" ? '<path d="M0 -3L2 0L0 3L-2 0ZM0 -2V2"/>' :
    style.family === "maker" ? '<circle cx="-2" cy="1" r="1"/><circle cx="2" cy="-2" r="1"/><path d="M-1 0L1 -1"/>' :
    style.family === "analyst" ? '<path d="M-2 -2H2M-2 0H2M-2 2H1"/>' :
    '<path d="M-2 -2H2V2H-2ZM0 -2V2M-2 0H2"/>';
  return `<g data-feature="wardrobe" data-family="${style.family}" data-presentation="${style.presentation}" data-flair="${style.flair}">
    ${avatarNeckMarkup(skin, mix)}
    <path data-feature="torso" d="${body}" fill="url(#shirt)" stroke="${edge}" stroke-width=".7" stroke-linejoin="round"/>
    <path d="M46 92${neckline}L82 93L88 135H40Z" fill="${pale}"/>
    ${feminine ? `<path d="M52 105Q60 112 57 125M76 105Q68 112 71 125" fill="none" stroke="${mix(pale, shirt, .4)}" stroke-width=".6" opacity=".7"/>` :
      masculine ? `<path d="M56 95L60 102L64 98L68 102L72 95M64 102V135" fill="none" stroke="${edge}" stroke-width=".6" opacity=".6"/>` : ""}
    ${garment}
    ${feminine ? `<path d="M40 107Q46 118 42 132M88 107Q82 118 86 132" fill="none" stroke="${edge}" stroke-width=".65" opacity=".65"/>` : ""}
    <path d="M78 112L89 111V113L78 114Z" fill="${accent}"/>
    ${style.flair === "bold" ? `<path d="M79 111L80 106L84 109L88 106L88 111Z" fill="${accent}" stroke="${edge}" stroke-width=".45"/>` : ""}
    <path d="M${shoulder + 5} 113L${waist - 3} 135M${123 - shoulder} 113L${131 - waist} 135" fill="none" stroke="${edge}" stroke-width=".75" opacity=".5"/>
    ${style.topstitch ? `<path d="M${shoulder + 7} 113L${waist - 1} 135M${121 - shoulder} 113L${129 - waist} 135" fill="none" stroke="${accent}" stroke-width=".45" opacity=".65"/>` : ""}
    ${style.emblem && style.family !== "creative" ? `<g transform="translate(84 118)" fill="none" stroke="${accent}" stroke-width=".65" stroke-linejoin="round">${motif}</g>` : ""}
  </g>`;
}

function avatarNamedWardrobeMarkup(style, skin, mix) {
  const design = avatarNamedOutfits[style.outfit];
  const [base, contrast, accent] = design.palette;
  const edge = mix(base, "#1c2330", .6);
  const shoulder = style.presentation === "feminine" ? 20 : style.presentation === "masculine" ? 14 : 17;
  const body = `M${shoulder - 3} 137L${shoulder} 111Q${shoulder + 3} 100 48 94L53 92Q64 101 75 92L80 94Q${125 - shoulder} 100 ${128 - shoulder} 111L${131 - shoulder} 137Z`;
  return `<g data-feature="wardrobe" data-outfit="${style.outfit}" data-family="${style.family}" data-presentation="${style.presentation}" data-flair="${style.flair}">
    ${avatarNeckMarkup(skin, mix)}
    <path data-feature="torso" d="${body}" fill="${base}" stroke="${edge}" stroke-width=".7"/>
    ${design.panels.map(([d, color]) => `<path d="${d}" fill="${design.palette[color]}" stroke="${edge}" stroke-width=".65" stroke-linejoin="round"/>`).join("")}
    <path d="${design.seams}" fill="none" stroke="${contrast}" stroke-width=".65" stroke-linecap="round" stroke-linejoin="round"/>
    ${design.jewel ? `<g data-feature="name-accessory" fill="${accent}" stroke="${edge}" stroke-width=".7" stroke-linejoin="round">${design.jewel}</g>` : ""}
    ${style.flair === "bold" ? `<path d="M24 114L29 133M104 114L99 133" fill="none" stroke="${accent}" stroke-width="1.3"/>` : ""}
  </g>`;
}

function avatarNamedBackdropMarkup(style) {
  if (!Object.hasOwn(avatarNamedOutfits, style.outfit)) return "";
  const design = avatarNamedOutfits[style.outfit];
  return `<g data-feature="name-backdrop" data-motif="${style.outfit}" fill="${design.palette[1]}" fill-opacity=".26" stroke="${design.palette[0]}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" opacity=".8">${design.prop}</g>`;
}

function avatarIndividualWardrobeMarkup(style, skin, mix) {
  const feminine = style.presentation === "feminine";
  const bold = style.flair === "bold";
  const shoulder = feminine ? 20 : style.presentation === "masculine" ? 14 : 17;
  const waist = feminine ? 38 : 32;
  const palettes = {
    "cable-knit": ["#82608a", "#d4a0b0", "#e7c296"],
    "cardboard-harness": ["#234237", "#d3aa6b", "#f1d8a1"],
    mandarin: ["#277873", "#8ac1ad", "#d1b273"],
    suspenders: ["#eee1c9", "#6a2c46", "#b58b51"],
    "chore-jacket": ["#b87a38", "#282b36", "#e9c68e"],
    "map-shirt": ["#255262", "#81a79a", "#e6c39b"],
    "mockneck-drape": ["#2b2b35", "#823f51", "#c5c6ce"],
    "linen-wrap": ["#ddcfb3", "#51777a", "#ad7958"],
    "tweed-cravat": ["#6e7353", "#e0d6bd", "#7d435d"],
    "zip-hoodie": ["#394152", "#5a88c3", "#cbd5e2"],
    "bib-overalls": ["#e6dcc4", "#44695d", "#b76b4e"],
    "shawl-cardigan": ["#a76047", "#e9d8b8", "#704d3e"],
    "embroidered-smock": ["#26394f", "#decda6", "#c98851"],
    "moto-jacket": ["#58364f", "#d9aa55", "#cad3d9"],
    "satin-bomber": ["#ad446c", "#e9dac4", "#284d53"],
    "breton-sling": ["#e6dfcc", "#263e58", "#b9813d"],
  };
  const [base, contrast, accent] = palettes[style.outfit];
  const edge = mix(base, "#20232e", .55);
  const body = `M${shoulder - 3} 137L${shoulder} 111Q${shoulder + 3} 100 48 94L53 92Q64 101 75 92L80 94Q${125 - shoulder} 100 ${128 - shoulder} 111L${131 - shoulder} 137Z`;
  let definitions = "", garment;
  if (style.outfit === "cable-knit") {
    definitions = '<pattern id="individual-knit" width="12" height="14" patternUnits="userSpaceOnUse"><path d="M3 0Q9 3 3 7Q-3 10 3 14M9 0Q3 3 9 7Q15 10 9 14" fill="none" stroke="#d4a0b0" stroke-width=".55" opacity=".6"/></pattern>';
    garment = `<path d="${body}" fill="url(#individual-knit)"/>
      <path d="M46 94Q64 ${bold ? 108 : 103} 82 94L83 99Q64 ${bold ? 114 : 109} 45 99Z" fill="${contrast}" stroke="${edge}" stroke-width=".55"/>
      <path d="M48 98Q64 108 80 98M29 110L35 136M99 110L93 136" fill="none" stroke="${edge}" stroke-width=".65"/>
      <path d="M55 102Q64 113 73 102" fill="none" stroke="${accent}" stroke-width=".5"/>
      <path d="M64 109L66 112L64 115L62 112Z" fill="${accent}"/>`;
  } else if (style.outfit === "cardboard-harness") {
    definitions = '<pattern id="individual-cardboard" width="9" height="7" patternUnits="userSpaceOnUse"><path d="M1 2H5M6 5H9" stroke="#80552e" stroke-width=".35" opacity=".35"/></pattern>';
    garment = `<path d="M46 95L51 97L49 109H43ZM82 95L77 97L79 109H85Z" fill="${accent}" stroke="#80552e" stroke-width=".6"/>
      <g data-feature="cardboard-box" stroke="#694626" stroke-width=".8" stroke-linejoin="round">
        <path d="M32 109H83V139H32Z" fill="${contrast}"/>
        <path d="M83 109L99 102V132L83 139Z" fill="#a87640"/>
        <path d="M32 109H83V139H32Z" fill="url(#individual-cardboard)"/>
        <path d="M32 109L43 99L64 104L54 113ZM64 104L85 99L101 105L83 113Z" fill="#e1bb7b"/>
        <path d="M35 108L43 102L61 106M68 106L85 102L97 105" fill="none" stroke="#ae7c42" stroke-width=".55"/>
        <path d="M56 110H63V139H56Z" fill="${accent}" stroke="none"/>
        <path d="M86 113L96 109M86 117L96 113M86 121L96 117M86 125L96 121" fill="none" opacity=".55"/>
        <g data-feature="kc-mark" fill="none" stroke="#3b2b1f" stroke-width="2.6" stroke-linecap="square">
          <path d="M41 117V129M42 123L50 117M43 122L51 129"/>
          <path d="M76 118C66 113 65 132 76 128"/>
        </g>
        ${bold ? '<path d="M36 115H45V118H36ZM73 132H80V135H73Z" fill="#a2733f" stroke="none"/>' : ""}
      </g>
      <g data-feature="box-headphones" fill="#263039" stroke="#151e23" stroke-width=".6">
        <path d="M28 117V113Q28 104 39 104M96 104Q103 105 103 114V119" fill="none" stroke-width="2"/>
        <rect x="26" y="115" width="6" height="12" rx="2"/>
        <rect x="99" y="114" width="6" height="12" rx="2"/>
      </g>`;
  } else if (style.outfit === "mandarin") {
    garment = `<path d="M52 96V91Q64 95 76 91V97L69 102H59Z" fill="${base}" stroke="${edge}" stroke-width=".65"/>
      <path d="M53 92Q64 97 75 92M68 99L72 137" fill="none" stroke="${accent}" stroke-width=".65"/>
      ${[102,111,120,129].map(y => `<circle cx="${68 + (y - 97) / 10}" cy="${y}" r=".85" fill="${accent}"/>`).join("")}
      <path d="M${shoulder + 1} 114L${waist - 5} 137M${127 - shoulder} 114L${133 - waist} 137" fill="none" stroke="${contrast}" stroke-width=".65"/>
      ${bold ? `<path d="M81 107H91V116H81Z" fill="${contrast}"/><path d="M83 106V113M86 106V112" stroke="${edge}" stroke-width=".65"/>` : ""}`;
  } else if (style.outfit === "suspenders") {
    garment = `<path d="M51 92L59 102L64 97L69 102L77 92L72 106L64 101L56 106Z" fill="#fff5df" stroke="${edge}" stroke-width=".55"/>
      <path d="M64 103V137" stroke="${accent}" stroke-width=".55"/>
      <path d="M38 97L43 95L49 137H42ZM90 97L85 95L79 137H86Z" fill="${contrast}" stroke="${edge}" stroke-width=".5"/>
      <g fill="${accent}" stroke="${edge}" stroke-width=".4"><rect x="40.5" y="115" width="6" height="7" rx=".8"/><rect x="81.5" y="115" width="6" height="7" rx=".8"/></g>
      <path d="M61 102H67L66 106L68 125L64 130L60 125L62 106Z" fill="${bold ? "#47746f" : "#45434d"}"/>
      <path d="M61 118H67" stroke="${accent}" stroke-width=".8"/>`;
  } else if (style.outfit === "chore-jacket") {
    garment = `<path d="M48 94Q64 105 80 94L83 137H45Z" fill="${contrast}"/>
      <path d="M48 94L56 99L55 137H16L21 110Q25 101 48 94ZM80 94L72 99L73 137H112L107 110Q103 101 80 94Z" fill="url(#individual-fabric)" stroke="${edge}" stroke-width=".65"/>
      <path d="M48 94L51 104L44 101L39 99ZM80 94L77 104L84 101L89 99Z" fill="${accent}" stroke="${edge}" stroke-width=".5"/>
      <path d="M29 111H47V124Q38 129 29 124ZM82 111H99V124Q90 129 82 124Z" fill="${mix(base, "#242834", .15)}" stroke="${accent}" stroke-width=".6"/>
      <path d="M30 114H46M83 114H98M53 105L52 137M75 105L76 137" fill="none" stroke="${accent}" stroke-width=".5"/>
      ${bold ? `<path d="M85 109L87 118M88 109L90 118" stroke="${contrast}" stroke-width="1"/>` : ""}`;
  } else if (style.outfit === "map-shirt") {
    definitions = '<pattern id="individual-map" width="25" height="22" patternUnits="userSpaceOnUse"><path d="M-4 5C3 -2 17 2 15 8S27 12 28 18M-3 11C4 4 11 7 9 12S20 17 27 14M0 19Q7 14 12 20T27 21" fill="none" stroke="#81a79a" stroke-width=".6" opacity=".85"/></pattern>';
    garment = `<path d="${body}" fill="url(#individual-map)"/>
      <path d="M50 93L64 ${bold ? 111 : 105}L78 93L72 106L64 111L56 106Z" fill="url(#neck)"/>
      <path d="M49 93L58 99L56 108L45 100ZM79 93L70 99L72 108L83 100Z" fill="${contrast}" stroke="${edge}" stroke-width=".6"/>
      <path d="M64 111V137" stroke="${accent}" stroke-width=".6"/>
      ${[116,125,134].map(y => `<circle cx="66" cy="${y}" r=".7" fill="${accent}"/>`).join("")}`;
  } else if (style.outfit === "mockneck-drape") {
    garment = `<path d="M53 97V90Q64 94 75 90V97Q64 102 53 97Z" fill="${base}" stroke="${edge}" stroke-width=".65"/>
      <path d="M54 93Q64 97 74 93M54 96Q64 100 74 96" fill="none" stroke="#747080" stroke-width=".45"/>
      <path d="M39 97L48 93Q52 106 88 122L99 137H70Q43 124 39 97Z" fill="${contrast}" stroke="${edge}" stroke-width=".65"/>
      <path d="M44 97Q51 114 91 132M42 102Q50 122 77 136" fill="none" stroke="#b17482" stroke-width=".6" opacity=".7"/>
      <path d="M48 97Q60 107 71 96" fill="none" stroke="${accent}" stroke-width=".6"/>
      ${bold ? `<path d="M46 99Q62 115 77 97" fill="none" stroke="${accent}" stroke-width=".45"/>` : ""}
      <path d="M47 95L50 99L47 102L44 99Z" fill="${accent}"/>`;
  } else if (style.outfit === "linen-wrap") {
    definitions = '<pattern id="individual-linen" width="4" height="5" patternUnits="userSpaceOnUse"><path d="M0 1H4M1 0V5" stroke="#856f57" stroke-width=".25" opacity=".3"/></pattern>';
    garment = `<path d="M49 94Q64 ${bold ? 110 : 104} 79 94L85 137H43Z" fill="${contrast}"/>
      <path d="M48 94L58 100L80 126L83 137H16L21 111Q24 102 48 94ZM80 94L70 100L45 126L44 137H112L107 111Q104 102 80 94Z" fill="url(#individual-fabric)" stroke="${edge}" stroke-width=".65"/>
      <path d="${body}" fill="url(#individual-linen)" opacity=".6"/>
      <path d="M50 96L76 127M78 96L47 128" stroke="#f3e8cd" stroke-width="1.8"/>
      <path d="M28 125Q64 130 100 125V130Q64 135 28 130Z" fill="${accent}" stroke="${edge}" stroke-width=".5"/>
      <ellipse cx="80" cy="128" rx="3" ry="2.1" fill="none" stroke="#e9cf9f" stroke-width=".9"/>`;
  } else if (style.outfit === "tweed-cravat") {
    definitions = '<pattern id="individual-tweed" width="5" height="6" patternUnits="userSpaceOnUse"><path d="M0 0L2.5 3L0 6M2.5 0L5 3L2.5 6" fill="none" stroke="#c0bc8f" stroke-width=".4" opacity=".65"/></pattern>';
    garment = `<path d="${body}" fill="${contrast}"/>
      <path d="M44 95L61 110L64 112L67 110L84 95L81 117L${94 - waist / 3} 137H${34 + waist / 3}L47 117Z" fill="${base}" stroke="${edge}" stroke-width=".65"/>
      <path d="M44 95L61 110L64 112L67 110L84 95L81 117L${94 - waist / 3} 137H${34 + waist / 3}L47 117Z" fill="url(#individual-tweed)"/>
      <path d="M52 95Q64 101 76 95L70 104L73 114L63 109L56 113L59 103Z" fill="${accent}" stroke="${edge}" stroke-width=".5"/>
      <path d="M58 98L64 103L69 98M64 104L61 110" fill="none" stroke="#b77e98" stroke-width=".5"/>
      ${[117,124,131].map(y => `<circle cx="64" cy="${y}" r=".8" fill="#c6a567"/>`).join("")}
      ${bold ? '<path d="M75 118Q70 129 67 124" fill="none" stroke="#d4bd7e" stroke-width=".5"/>' : ""}`;
  } else if (style.outfit === "zip-hoodie") {
    garment = `<g data-feature="hood-sides" fill="${base}" stroke="${edge}" stroke-width=".75">
        <path d="M35 101Q34 90 49 88L55 92Q45 94 49 102L44 109Z"/>
        <path d="M35 101Q34 90 49 88L55 92Q45 94 49 102L44 109Z" transform="translate(128 0) scale(-1 1)"/>
      </g>
      <g fill="${contrast}" stroke="${edge}" stroke-width=".5">
        <path d="M40 100Q39 93 49 91L52 94Q46 96 49 103L45 105Z"/>
        <path d="M40 100Q39 93 49 91L52 94Q46 96 49 103L45 105Z" transform="translate(128 0) scale(-1 1)"/>
      </g>
      <path data-feature="hood-opening" d="M52 95Q64 104 76 95L79 99Q64 109 49 99Z" fill="${base}" stroke="${edge}" stroke-width=".7"/>
      <path d="M76 101L63 137" stroke="${accent}" stroke-width="1.3"/><path d="M78 101L65 137" stroke="${edge}" stroke-width=".7"/>
      <path d="M48 103L45 115M80 103L83 115" stroke="${accent}" stroke-width=".7" stroke-linecap="round"/>
      <path d="M30 121L45 118L50 136M91 120L80 118L75 136" fill="none" stroke="${contrast}" stroke-width=".8"/>
      ${bold ? `<path d="M27 109L42 106M87 108L100 112" stroke="${contrast}" stroke-width="2"/>` : ""}`;
  } else if (style.outfit === "bib-overalls") {
    garment = `<path d="M47 94Q33 97 23 105L18 137H36L43 109ZM81 94Q95 97 105 105L110 137H92L85 109Z" fill="${accent}"/>
      <path d="M43 95L49 97L52 114H44ZM85 95L79 97L76 114H84Z" fill="${contrast}" stroke="${edge}" stroke-width=".6"/>
      <path d="M43 110Q64 114 85 110L89 137H39Z" fill="${contrast}" stroke="${edge}" stroke-width=".7"/>
      <path d="M53 118H76V130Q64 134 53 130Z" fill="${mix(contrast, "#1c3031", .15)}" stroke="#c9bc88" stroke-width=".6"/>
      <path d="M55 120H74M47 113L44 137M81 113L84 137" fill="none" stroke="#c9bc88" stroke-width=".5"/>
      <g fill="#c6a16c"><circle cx="47" cy="112" r="1.2"/><circle cx="81" cy="112" r="1.2"/></g>
      ${bold ? `<path d="M70 116L71 126M73 116L74 125" stroke="${accent}" stroke-width="1"/>` : ""}`;
  } else if (style.outfit === "embroidered-smock") {
    garment = `<path d="M47 95L54 94V101H74V94L81 95L85 112Q64 120 43 112Z" fill="${contrast}" stroke="${edge}" stroke-width=".65"/>
      <path d="M56 96H72L70 106H58Z" fill="url(#neck)"/>
      <path d="M54 95V102H74V95M46 110Q64 117 82 110" fill="none" stroke="${accent}" stroke-width="1"/>
      ${[48,55,62,69,76].map(x => `<path d="M${x} 109L${x + 3} 112M${x + 3} 109L${x} 112" stroke="${base}" stroke-width=".7"/>`).join("")}
      <path d="M33 105L38 137M95 105L90 137M48 119L45 137M80 119L83 137" fill="none" stroke="${mix(base, contrast, .35)}" stroke-width=".7"/>
      <path d="M51 124Q64 129 77 124" fill="none" stroke="${accent}" stroke-width=".65"/>
      ${bold ? `<path d="M31 119L35 123L31 127L27 123ZM97 119L101 123L97 127L93 123Z" fill="${accent}"/>` : ""}`;
  } else if (style.outfit === "moto-jacket") {
    garment = `<path d="M49 94Q64 104 79 94L84 137H44Z" fill="${contrast}"/>
      <path d="M48 94L57 100L82 137H16L21 110Q25 101 48 94ZM80 94L71 99L48 137H112L107 110Q103 101 80 94Z" fill="url(#individual-fabric)" stroke="${edge}" stroke-width=".75"/>
      <path d="M47 95L60 107L52 114L41 100ZM80 95L68 106L75 113L87 99Z" fill="${mix(base, "#b98ca1", .3)}" stroke="${edge}" stroke-width=".7"/>
      <path d="M77 106L53 137M31 116L43 111M86 120L97 115" stroke="${accent}" stroke-width="1.1"/>
      <path d="M78 107L54 137M30 118L42 113M87 122L98 117" stroke="${edge}" stroke-width=".5"/>
      <g fill="${accent}"><circle cx="49" cy="100" r="1"/><circle cx="79" cy="100" r="1"/><circle cx="55" cy="108" r=".8"/></g>
      ${bold ? `<path d="M28 105L38 102M90 102L100 105" stroke="${accent}" stroke-width="1.8"/>` : ""}`;
  } else if (style.outfit === "satin-bomber") {
    garment = `<path d="M48 94L43 110L35 137H16L21 110Q25 100 48 94ZM80 94L85 110L93 137H112L107 110Q103 100 80 94Z" fill="${contrast}" stroke="${edge}" stroke-width=".65"/>
      <path d="M50 94Q64 102 78 94L79 99Q64 109 49 99Z" fill="${accent}" stroke="${edge}" stroke-width=".6"/>
      <path d="M51 97Q64 105 77 97M64 104V136" fill="none" stroke="${contrast}" stroke-width=".8"/>
      ${[108,112,116,120,124,128].map(y => `<path d="M63 ${y}H65" stroke="${accent}" stroke-width=".65"/>`).join("")}
      <path d="M31 131Q64 135 97 131V137H31Z" fill="${accent}"/>
      <path d="M32 134Q64 138 96 134M43 104L34 130M85 104L94 130" fill="none" stroke="${contrast}" stroke-width=".7"/>
      <path d="M40 118L48 115M80 115L88 118" stroke="${edge}" stroke-width="1"/>
      ${bold ? `<path d="M82 108L86 112L82 116L78 112Z" fill="${contrast}" stroke="${accent}" stroke-width=".7"/>` : ""}`;
  } else if (style.outfit === "breton-sling") {
    definitions = '<pattern id="individual-breton" width="8" height="7" patternUnits="userSpaceOnUse"><path d="M0 3H8" stroke="#263e58" stroke-width="2.1"/></pattern>';
    garment = `<path d="${body}" fill="url(#individual-breton)"/>
      <path d="M50 94Q64 103 78 94L78 98Q64 108 50 98Z" fill="${contrast}" stroke="${edge}" stroke-width=".6"/>
      <path d="M39 98L47 95L91 137H79Z" fill="${accent}" stroke="${edge}" stroke-width=".7"/>
      <path d="M43 98L83 137" stroke="${mix(accent, "#f5dec0", .5)}" stroke-width=".6"/>
      <g transform="rotate(-12 78 124)">
        <rect x="65" y="115" width="27" height="19" rx="3" fill="${accent}" stroke="${edge}" stroke-width=".8"/>
        <path d="M66 119H91M69 121V129H88V121" fill="none" stroke="${edge}" stroke-width=".6"/>
        <rect x="76" y="116" width="5" height="4" rx=".7" fill="${contrast}" stroke="${mix(accent, "#f5dec0", .5)}" stroke-width=".5"/>
      </g>
      ${bold ? `<path d="M24 111L30 109M98 109L104 111" stroke="${accent}" stroke-width="2"/>` : ""}`;
  } else {
    garment = `<path d="M49 94Q64 105 79 94L82 137H46Z" fill="${contrast}"/>
      <path d="M61 101V118" stroke="${edge}" stroke-width=".65"/>
      <g fill="${accent}"><circle cx="64" cy="106" r=".65"/><circle cx="64" cy="111" r=".65"/><circle cx="64" cy="116" r=".65"/></g>
      <path d="M48 94Q38 108 51 137H17L21 110Q26 99 48 94ZM80 94Q90 108 77 137H111L107 110Q102 99 80 94Z" fill="url(#individual-fabric)" stroke="${edge}" stroke-width=".7"/>
      <path d="M49 94Q37 107 50 137H57Q43 107 55 96ZM79 94Q91 107 78 137H71Q85 107 73 96Z" fill="${mix(base, "#f7d8af", .2)}" stroke="${edge}" stroke-width=".6"/>
      <path d="M46 98Q38 111 53 136M82 98Q90 111 75 136M28 114L33 137M31 113L36 137M100 114L95 137M97 113L92 137" fill="none" stroke="${accent}" stroke-width=".5"/>
      ${bold ? `<path d="M28 123H39V133H29ZM89 123H100L99 133H89Z" fill="${mix(base, "#292734", .13)}" stroke="${accent}" stroke-width=".5"/>` : ""}`;
  }
  return `<g data-feature="wardrobe" data-outfit="${style.outfit}" data-family="${style.family}" data-presentation="${style.presentation}" data-flair="${style.flair}">
    <defs><linearGradient id="individual-fabric" x2="1" y2=".6"><stop stop-color="${mix(base, "#fff1d5", .13)}"/><stop offset=".5" stop-color="${base}"/><stop offset="1" stop-color="${mix(base, "#252838", .2)}"/></linearGradient>${definitions}</defs>
    ${avatarNeckMarkup(skin, mix)}
    <path data-feature="torso" d="${body}" fill="url(#individual-fabric)" stroke="${edge}" stroke-width=".7" stroke-linejoin="round"/>
    ${garment}
  </g>`;
}

function avatarPamWardrobeMarkup(style, skin, mix) {
  return `<g data-feature="wardrobe" data-theme="pam" data-family="executive" data-presentation="${style.presentation}" data-flair="${style.flair}">
    <path data-feature="torso" d="M14 136L18 111Q21 101 47 95L55 91H73L81 95Q105 101 109 111L114 136Z" fill="url(#shirt)" stroke="#102c34" stroke-width=".7"/>
    ${avatarNeckMarkup(skin, mix)}
    <g data-feature="ivory-blouse">
      <path d="M44 96L55 92Q64 100 73 92L84 96L88 136H40Z" fill="#eee7d9" stroke="#b3a68e" stroke-width=".55"/>
      <path data-feature="open-blouse-neckline" d="M55 92Q64 100 73 92L75 103Q72 113 64 122Q56 113 53 103Z" fill="url(#skin)"/>
      <path d="M51 94L60 113L52 109L46 100ZM77 94L68 113L76 109L82 100Z" fill="#fff5e3" stroke="#c6b8a0" stroke-width=".6"/>
      <path d="M64 122L65 136M45 115Q51 116 56 123M83 115Q77 116 72 123M49 130L57 134M79 129L71 134" fill="none" stroke="#bdb09d" stroke-width=".6"/>
      <circle cx="65" cy="130" r=".7" fill="#b9a98c"/>
    </g>
    <g data-feature="teal-blazer" fill="#1b4853" stroke="#102c34" stroke-width=".7">
      <path d="M43 95L51 105L47 111L51 136H22L28 107ZM85 95L77 105L81 111L77 136H106L100 107Z"/>
      <path d="M43 95L51 105L46 111L52 136L36 117L39 108L33 103Z" fill="#244f59"/>
      <path d="M85 95L77 105L82 111L76 136L92 117L89 108L95 103Z" fill="#173c46"/>
      <path d="M28 117L25 136M97 116L102 136" fill="none" stroke="#3b6870" stroke-width=".8"/>
    </g>
    <g data-feature="gold-pendant" fill="none" stroke="url(#gold)" stroke-width=".7">
      <path d="M55 96Q57 104 64 106Q71 103 73 96M55 97Q57 110 64 114Q71 110 73 97"/>
      <path d="M64 113L64 118M62.5 115H65.5" stroke-width=".9" stroke-linecap="round"/>
      <circle cx="64" cy="106" r="1" fill="url(#gold)" stroke-width=".4"/>
    </g>
    <g data-feature="pam-name-badge">
      <rect x="25" y="113" width="25" height="9.5" rx="1.1" fill="url(#gold)" stroke="#765321" stroke-width=".5"/>
      <path d="M27 116Q28 114 29 116Q30 114 31 116Q31 118 29 119Q27 118 27 116Z" fill="none" stroke="#795928" stroke-width=".45"/>
      <text x="39" y="117.7" text-anchor="middle" fill="#3c2b1c" font-family="sans-serif" font-size="3.7" font-weight="700">PAM</text>
      <text x="37.5" y="120.5" text-anchor="middle" fill="#3c2b1c" font-family="sans-serif" font-size="1.7" font-weight="600">EXECUTIVE ASSISTANT</text>
    </g>
    ${style.flair === "bold" ? '<path d="M34 110L37 108L40 110L37 113Z" fill="url(#gold)"/>' : ""}
  </g>`;
}

function avatarButlerWardrobeMarkup(skin, mix) {
  return `<g data-feature="wardrobe" data-theme="butler" data-family="formal" data-presentation="masculine" data-flair="restrained">
    <path data-feature="torso" d="M15 136L19 110Q23 100 48 94L55 91H73L80 94Q105 100 109 110L113 136Z" fill="#222630" stroke="#11141b" stroke-width=".7"/>
    ${avatarNeckMarkup(skin, mix)}
    <path d="M50 94L64 99L78 94L81 136H47Z" fill="#e8e4db" stroke="#a9a69e" stroke-width=".5"/>
    <path d="M51 92L64 99L56 105L49 96ZM77 92L64 99L72 105L79 96Z" fill="#faf7ef" stroke="#a9a69e" stroke-width=".5"/>
    <path d="M47 95L56 105L51 111L61 136L40 114L44 108L36 103ZM81 95L72 105L77 111L67 136L88 114L84 108L92 103Z" fill="#343a45" stroke="#11151d" stroke-width=".65"/>
    <g data-feature="bow-tie" fill="#1b1b20" stroke="#08090d" stroke-width=".5"><path d="M63 101L56 98L56 105L63 103ZM65 101L72 98L72 105L65 103Z"/><rect x="62" y="100" width="4" height="4" rx="1"/></g>
    <path d="M64 106V135M86 113H98" fill="none" stroke="#aaa79f" stroke-width=".6"/>
    ${[113,121,129].map(y => `<circle cx="64" cy="${y}" r=".7" fill="#7a7c7f"/>`).join("")}
    <path data-feature="watch-chain" d="M69 121Q77 128 85 120" fill="none" stroke="#bab9ad" stroke-width=".75"/>
    <path d="M88 111L91 107L93 111L95 108L97 112Z" fill="#efebe2"/>
  </g>`;
}

function avatarGothWardrobeMarkup(style, skin, mix) {
  const feminine = style.presentation === "feminine";
  const bold = style.flair === "bold";
  const body = "M17 136L20 110Q23 102 48 97Q55 95 55 91V80H73V91Q73 95 80 97Q105 102 108 110L111 136Z";
  const dress = feminine ?
    `M35 107Q45 100 54 103L64 ${bold ? 109 : 105}L74 103Q83 100 93 107L85 119L84 137H44L43 119Z` :
    style.presentation === "masculine" ?
      "M23 104L48 94L53 87L64 93L75 87L80 94L105 104L111 137H17Z" :
      "M23 104L47 95Q64 104 81 95L105 104L111 137H17Z";
  return `<g data-feature="wardrobe" data-theme="goth" data-family="creative" data-presentation="${style.presentation}" data-flair="${style.flair}">
    <defs>
      <linearGradient id="goth-velvet" x1="0" y1="0" x2="1" y2=".6"><stop stop-color="#292334"/><stop offset=".35" stop-color="#100e17"/><stop offset=".7" stop-color="#211927"/><stop offset="1" stop-color="#090912"/></linearGradient>
      <linearGradient id="goth-silver" x2="1" y2="1"><stop stop-color="#e0e0e9"/><stop offset=".5" stop-color="#817c91"/><stop offset="1" stop-color="#cbc8d8"/></linearGradient>
      <pattern id="goth-lace" patternUnits="userSpaceOnUse" width="6" height="6"><path d="M3 0L6 3L3 6L0 3ZM3 1Q6 3 3 5Q0 3 3 1Z" fill="none" stroke="#76647c" stroke-width=".35"/></pattern>
      <clipPath id="goth-dress"><path d="${dress}"/></clipPath>
    </defs>
    <path data-feature="torso" d="${body}" fill="url(#skin)" stroke="${mix(skin, "#38292c", .38)}" stroke-width=".65"/>
    ${avatarNeckMarkup(skin, mix)}
    <path d="M56 98Q50 100 42 100M72 98Q78 100 86 100" fill="none" stroke="${mix(skin, "#533a45", .28)}" stroke-width=".6" opacity=".65"/>
    <g fill="url(#goth-velvet)" stroke="#4b3b52" stroke-width=".6">
      <path d="M21 105Q29 100 39 105L44 111L37 137H17Z"/>
      <path d="M21 105Q29 100 39 105L44 111L37 137H17Z" transform="translate(128 0) scale(-1 1)"/>
      <path data-feature="goth-dress" d="${dress}"/>
    </g>
    <g clip-path="url(#goth-dress)">
      <rect x="17" y="95" width="94" height="44" fill="url(#goth-lace)" opacity=".55"/>
      <path d="M47 109Q51 121 47 137M58 111V137M70 111V137M81 109Q77 121 81 137" fill="none" stroke="#685164" stroke-width=".7" opacity=".65"/>
    </g>
    ${feminine ? `<path data-feature="lace-neckline" d="M36 107Q39 103 42 106Q45 102 48 105Q51 102 54 105L64 ${bold ? 110 : 106}L74 105Q77 102 80 105Q83 102 86 106Q89 103 92 107" fill="none" stroke="#968198" stroke-width=".65"/>
      <path d="M21 106Q30 102 39 108M107 106Q98 102 89 108" fill="none" stroke="#9a869d" stroke-width=".7"/>
      <g fill="url(#goth-silver)">${[116,122,128,134].map(y => `<circle cx="60.5" cy="${y}" r=".65"/><circle cx="67.5" cy="${y}" r=".65"/>`).join("")}</g>
      <path d="M61 116L67 122L61 128L67 134M67 116L61 122L67 128L61 134" fill="none" stroke="#ab93a9" stroke-width=".55"/>` :
      `<path d="M48 95L58 108L52 112L64 135L76 112L70 108L80 95" fill="none" stroke="#85748d" stroke-width=".8"/>
      <path d="M64 108V137" stroke="#a9a0b6" stroke-width=".6"/>`}
    <g data-feature="choker">
      <path d="M54 91Q64 94 74 91V95Q64 98 54 95Z" fill="#17121d" stroke="#76617d" stroke-width=".45"/>
      ${[55.5,59.75,64,68.25,72.5].map(x => `<circle cx="${x}" cy="${95 + (1 - Math.abs(64 - x) / 10)}" r=".6" fill="url(#goth-silver)"/>`).join("")}
      <path d="M64 97L66 100L64 103L62 100Z" fill="#572b48" stroke="url(#goth-silver)" stroke-width=".55"/>
      ${bold ? '<path d="M48 96Q64 108 80 96" fill="none" stroke="#a69aaa" stroke-width=".5"/><circle cx="64" cy="102" r=".8" fill="url(#goth-silver)"/>' : ""}
    </g>
  </g>`;
}

function avatarStudyDataUri(seed, version, persona = {}, appearance = {}) {
  if ([3, 4, 5].includes(version)) return avatarEarlyStudyDataUri(seed, version);
  if (![6, 7, 8, 9].includes(version)) throw new RangeError("Unknown avatar study version");
  const tailored = version === 9;
  const wardrobe = tailored ? avatarWardrobeProfile(seed, persona, appearance) : null;
  const goth = wardrobe?.theme === "goth";
  const butler = wardrobe?.theme === "butler";
  const pam = wardrobe?.theme === "pam";
  const kissWink = wardrobe?.expression === "kiss-wink";
  const friendlyWink = wardrobe?.expression === "friendly-wink" || kissWink;
  const { background, skin, hair, shirt, hairStyle, eyeStyle, mouthStyle, accessory,
    faceWidth, faceHeight, eyeSpacing, eyeColor, eyebrowTilt } = {
    ...avatarRecipe(seed),
    ...(goth ? { background: "#282238", hair: "#17131e", shirt: "#18121e",
      hairStyle: 4, eyeStyle: 0, mouthStyle: 4, accessory: 3 } : {}),
    ...(butler ? { background: "#cbd2cf", skin: "#d9b395", hair: "#a9a8a2", shirt: "#222630",
      hairStyle: 7, eyeStyle: 0, mouthStyle: 0, accessory: 0, faceWidth: 26, faceHeight: 34,
      eyeColor: "#6d7f87" } : {}),
    ...(pam ? { background: "#79634e", skin: "#d99b72", hair: "#241c19", shirt: "#174652",
      hairStyle: 4, eyeStyle: 0, mouthStyle: 3, accessory: 3, faceWidth: 24, faceHeight: 32,
      eyeColor: "#78533a" } : {}),
  };
  const graphic = version === 6;
  const refined = version === 8 || tailored;
  const mix = (a, b, t) => `#${[1, 3, 5].map(i =>
    Math.round(parseInt(a.slice(i, i + 2), 16) * (1 - t) + parseInt(b.slice(i, i + 2), 16) * t)
      .toString(16).padStart(2, "0")).join("")}`;
  let state = 2166136261;
  for (const c of `atelier:${seed.toLowerCase()}`) state = Math.imul(state ^ c.charCodeAt(0), 16777619) >>> 0;
  const n = shift => ((state >>> shift) & 31) / 31;
  const dark = refined ? mix(skin, "#38292c", .29) : mix(skin, "#482e35", .42);
  const deep = mix(skin, "#30232c", .73);
  const light = mix(skin, refined ? "#ffe6bc" : "#fff0d6", refined ? .14 : .25);
  const hairDark = mix(hair, "#1c202b", .58);
  const hairLight = mix(hair, goth ? "#8c729a" : "#ead4af", goth ? .26 : .3);
  const brow = mix(hair, "#352c31", .58);
  const hasLipstick = goth || wardrobe?.presentation === "feminine";
  const lipstickShades = ["#64252b", "#8d2539", "#b82540", "#c63e50", "#b95c70", "#d97695", "#ec9eb4"];
  const lip = hasLipstick ? (goth ? lipstickShades[0] : pam ? "#aa4246" : lipstickShades[state % lipstickShades.length]) : mix(skin, "#994e53", .34);
  const w = faceWidth - 1.4;
  const bottom = faceHeight + 61.2;
  const jaw = 14.5 + n(3) * 4.5;
  const turn = (n(8) - .5) * 4.8;
  const pose = `${tailored ? "translate(0 -9) " : ""}rotate(${turn.toFixed(2)} 64 67)`;
  const head = `M${64 - w} 52C${63 - w} 34 47 ${60 - faceHeight} 63 ${60 - faceHeight}
    C80 ${60 - faceHeight} ${64 + w} 34 ${64 + w} 51
    C${65 + w} 63 ${62 + w} 75 ${65 + jaw} 84
    Q75 ${bottom} 64 ${bottom + 1}Q54 ${bottom} ${64 - jaw} 85
    C${66 - w} 76 ${63 - w} 64 ${64 - w} 52Z`;
  const fronts = [
    '<path d="M32 53C29 40 31 28 41 22C52 15 73 14 85 21Q99 29 96 46L92 56L85 39Q75 43 66 36Q53 31 44 39L38 55Z"/>',
    '<path d="M32 55C23 38 29 24 42 21C62 9 89 13 96 29Q102 40 94 56L86 46L83 31C74 44 55 48 39 44L38 57Z"/>',
    '<path d="M31 53C24 46 25 36 30 33C24 23 33 16 42 18C47 8 59 11 64 17C72 10 84 13 88 23C99 21 107 34 98 43L96 55Q88 52 85 43Q78 48 73 37Q64 44 57 36Q48 43 40 41L37 56Z"/>',
    '<path d="M30 61L31 38C31 12 95 8 98 39L94 68L85 42L77 34Q59 45 40 39L37 64Z"/>',
    '<path d="M30 61C22 30 35 17 54 16C77 8 104 22 98 46L93 70L82 37Q62 49 42 40L37 68Z"/>',
    '<path d="M31 54C27 42 28 29 37 26L44 31L48 19L57 25L69 13L78 25L89 21L92 35L99 37L95 55L84 41L69 37L51 34L39 45Z"/>',
    '<path d="M32 56C25 29 36 18 57 19C78 12 100 23 97 48L89 58L82 36Q62 44 42 36L38 57Z"/>',
    '<path d="M33 53Q28 44 35 36L41 43L39 58ZM89 43L95 35Q102 46 94 55L89 58Z"/>',
  ];
  if (butler) fronts[7] = '<path d="M39 59C34 51 35 41 43 34Q39 44 43 55L42 61ZM89 59C94 51 93 41 85 34Q89 44 85 55L86 61Z"/>';
  if (pam) fronts[4] = '<path d="M29 62C20 37 31 18 51 16C71 7 99 18 99 39Q101 51 94 67L90 83Q97 97 90 114L83 110Q90 93 83 82L84 50L80 33Q68 48 48 48Q40 48 38 61L35 79Q27 90 34 104L28 117Q19 103 24 88L29 75Z"/>';
  if (goth) fronts[4] = '<path d="M30 63C24 37 31 19 50 16C73 6 103 20 99 47L102 107Q101 120 96 125L88 118L86 55L83 39Q82 43 78 46Q75 44 75 40Q74 45 69 47Q67 44 67 41Q65 45 61 46Q59 43 59 40Q57 44 53 46Q50 43 50 40Q47 44 43 45L39 56L38 111L29 124L23 118L28 93Z"/>';
  const rear = goth ? '<path d="M30 43C25 17 42 13 61 14C83 9 104 25 100 49L104 92Q110 109 100 131L88 123L79 105H49L42 126L24 132Q18 111 24 92Z"/>' : [
    "", "",
    '<path d="M32 43C21 52 24 84 33 98L45 90H82L96 99C108 85 105 53 96 42Z"/>',
    '<path d="M31 52C21 8 107 6 98 55L100 100L79 99L76 91H50L48 101L27 100Z"/>',
    '<path d="M30 49C21 9 106 5 99 58L106 120L83 117L75 91H51L43 117L22 120Z"/>',
    "",
    '<path d="M76 28C65 18 74 7 87 8C103 7 108 27 94 33Z"/>',
    "",
  ][hairStyle];
  const strand = butler ? "M39 42Q37 49 40 56M89 42Q91 49 88 56" : pam ? "M32 43C27 26 49 18 67 21M39 42Q61 44 79 25M43 46Q64 47 82 29M85 34Q96 44 90 60M32 65Q26 79 30 88Q37 99 29 111M90 67Q86 80 91 89Q95 99 87 109" : goth ? "M34 42C31 26 48 18 60 20M38 40Q44 32 48 26M52 39Q57 33 60 24M66 39L65 23M76 39Q72 31 71 24M84 34Q94 39 93 56M33 57Q31 87 28 113M94 61Q97 93 96 115M37 77Q35 101 32 115M90 82L93 112" : [
    "M33 39C40 22 64 20 82 25M36 43C43 29 61 24 77 28M43 40Q54 30 64 35M67 28Q78 36 88 32M87 35Q93 41 92 47",
    "M33 39C29 29 38 21 53 22M37 39C54 44 73 31 81 24M40 43C57 47 76 35 85 28M87 28Q95 35 93 47",
    "M29 36Q32 26 40 34M34 25Q41 18 46 27M48 20Q57 13 61 23M68 20Q77 16 81 27M86 29Q96 26 97 37M84 40Q94 35 96 47",
    "M34 40C32 20 63 18 80 24M41 35Q61 41 79 28M85 34Q92 45 93 57M34 63L33 91M94 69L96 94",
    "M34 41C30 24 51 18 68 21M41 35Q60 43 82 28M87 35Q95 48 92 60M35 68Q30 92 28 113M94 70Q96 96 100 113",
    "M33 39L40 42M44 30L50 35M54 31L68 20L73 31M77 32L86 27L86 37M91 41L96 40",
    "M35 39C33 24 53 20 70 23M42 35Q63 40 83 28M47 38Q68 42 84 32M88 33Q94 40 93 49",
    "M34 43L37 49M94 43L92 49",
  ][hairStyle];
  const eyeY = 59.5;
  const eyeW = tailored ? 8.3 : 6.05;
  const opening = eyeStyle === 1 ? (tailored ? 4.3 : 2.7) : (tailored ? 3.8 : 2.15);
  const clips = [];
  const eyes = [64 - eyeSpacing, 64 + eyeSpacing].map((x, i) => {
    if (friendlyWink && i === 1) {
      return `<g data-eye="closed" data-expression="wink"><path data-feature="wink-lid" d="M${x - 7.5} ${eyeY + .7}Q${x} ${eyeY - 5.8} ${x + 7.5} ${eyeY + .2}" fill="none" stroke="${brow}" stroke-width="1.6" stroke-linecap="round"/>
        <path data-feature="wink-cheek" d="M${x - 4.8} ${eyeY + 3.8}Q${x} ${eyeY + 1.4} ${x + 5.3} ${eyeY + 3.4}" fill="none" stroke="${dark}" stroke-width=".7" opacity=".65"/></g>`;
    }
    if (!tailored && (eyeStyle === 2 || (eyeStyle === 3 && i === 1))) {
      return `<g data-eye="closed"><path d="M${x - (tailored ? 7.5 : 5.8)} ${eyeY}Q${x} ${eyeY + (tailored ? 4.1 : 3)} ${x + (tailored ? 7.5 : 5.8)} ${eyeY - .1}" fill="none" stroke="${brow}" stroke-width="1.25" stroke-linecap="round"/>
        <path d="M${x - 4.5} ${eyeY + 2.8}Q${x} ${eyeY + 4.6} ${x + 4.5} ${eyeY + 2.5}" fill="none" stroke="${dark}" stroke-width=".6" opacity=".55"/></g>`;
    }
    const upperLeft = eyeY - opening - (refined && i === 1 ? 1 : .5);
    const upperRight = eyeY - opening - (refined && i === 1 ? .5 : 1);
    const shape = `M${x - eyeW} ${eyeY}C${x - 3.8} ${upperLeft} ${x + 2.8} ${upperRight} ${x + eyeW} ${eyeY - .2}Q${x + .4} ${eyeY + opening + 1} ${x - eyeW} ${eyeY}Z`;
    clips.push(`<clipPath id="eye-${i}"><path d="${shape}"/></clipPath>`);
    const gaze = (n(12) - .5) * 1.1;
    return `<g data-eye="open"><path d="${shape}" fill="${graphic ? "#e9e1d3" : "url(#white)"}"/>
      <g clip-path="url(#eye-${i})"><circle cx="${x + gaze}" cy="${eyeY - .2}" r="${tailored ? 3.65 : 2.7}" fill="${refined ? mix(eyeColor, "#38302c", .18) : eyeColor}" stroke="${mix(eyeColor, "#202735", .6)}" stroke-width=".6"/>
      <circle cx="${x + gaze}" cy="${eyeY - .2}" r="${tailored ? 1.25 : refined ? 1.05 : 1.25}" fill="#24232c"/><circle cx="${x + gaze - .6}" cy="${eyeY - .9}" r="${tailored ? .35 : refined ? .3 : .38}" fill="#fff1d9"/>
      <path d="M${x - eyeW} ${eyeY - .7}Q${x} ${eyeY - 5} ${x + eyeW} ${eyeY - .7}" fill="none" stroke="${deep}" stroke-width="1.8" opacity=".35"/></g>
      <path d="M${x - eyeW} ${eyeY}C${x - 3.8} ${upperLeft} ${x + 2.8} ${upperRight} ${x + eyeW} ${eyeY - .2}" fill="none" stroke="${brow}" stroke-width="${graphic ? 1.4 : 1.05}" stroke-linecap="round"/>
      <path d="M${x - 5} ${eyeY + .7}Q${x + .5} ${eyeY + opening + .8} ${x + 5.6} ${eyeY + .3}" fill="none" stroke="${dark}" stroke-width=".6" opacity=".8"/>
      <path d="M${x - 4.9} ${eyeY - 4.5}Q${x + .4} ${eyeY - 6} ${x + 5.5} ${eyeY - 3.3}" fill="none" stroke="${dark}" stroke-width=".65" opacity=".6"/></g>`;
  }).join("");
  const eyebrows = [64 - eyeSpacing, 64 + eyeSpacing].map((x, i) => {
    const lift = friendlyWink ? (i ? 1.7 : -1.6) : i ? eyebrowTilt * 1.1 : -.3;
    return `<path d="M${x - (tailored ? 7.8 : 6.5)} ${51.4 + lift}Q${x - 1.5} ${48.8 + lift} ${x + (tailored ? 7.5 : 6.1)} ${50.8 - lift}L${x + (tailored ? 6.9 : 5.5)} ${52 - lift}Q${x - 1} ${51 + lift} ${x - (tailored ? 7.8 : 6.5)} ${52.4 + lift}Z"/>`;
  }).join("");
  const mouths = [
    `<path d="M56 82Q64 86 73 80.8" fill="none" stroke="${mix(lip, deep, .2)}" stroke-width="1.2" stroke-linecap="round"/><path d="M60 85.6Q64 86.9 69 84.9" fill="none" stroke="${light}" stroke-width=".65"/>`,
    `<path d="M53.8 80.7Q64 84 74 80Q72 89 64 89.2Q56 89 53.8 80.7Z" fill="${deep}"/><path d="M55.2 81.5Q64 84.2 72.7 81L71.5 83.6Q64 85.4 56.4 84Z" fill="#e9dfce"/><path d="M59.6 87.6Q64 85.5 68.5 87.4" fill="none" stroke="${lip}" stroke-width="1.2"/><path d="M54 80.5Q64 83.7 74 79.9" fill="none" stroke="${lip}" stroke-width=".7"/>`,
    `<path d="M58 81Q64 79.3 70 81.2Q69 86.3 64 86.5Q60 86.3 58 81Z" fill="${deep}"/><path d="M60 85.4Q64 83.5 68 85.2" fill="none" stroke="${lip}" stroke-width="1"/><path d="M58 80.7Q64 78.9 70 81" fill="none" stroke="${lip}" stroke-width=".75"/>`,
    `<path d="M56.5 82.4Q65 85.3 73 79.7" fill="none" stroke="${mix(lip, deep, .25)}" stroke-width="1.15" stroke-linecap="round"/><path d="M72 79L74 79.4" stroke="${dark}" stroke-width=".7"/>`,
    `<path d="M57.5 82Q61.5 80 64 81.2Q67 80 70.7 82.2Q64.5 85 57.5 82Z" fill="${lip}" opacity=".72"/><path d="M58 82Q64 83.2 70.2 82" fill="none" stroke="${deep}" stroke-width=".65"/><path d="M61 84Q65 84.6 68 83.7" fill="none" stroke="${light}" stroke-width=".55"/>`,
  ];
  const earX = [64 - w - 1.7, 64 + w + 1.7];
  const earrings = earX.map((x, i) => `<g data-earring="${i ? "right" : "left"}">${goth ?
    `<circle cx="${x}" cy="71" r=".85" fill="url(#goth-silver)"/><path d="M${x} 72V74" stroke="#b6aabd" stroke-width=".65"/><path d="M1 -2.6A2.8 2.8 0 1 0 1 2.6A2.1 2.1 0 0 1 1 -2.6Z" transform="translate(${x} 76.5)" fill="url(#goth-silver)" stroke="#77647d" stroke-width=".4"/>` :
    pam ?
    `<circle cx="${x}" cy="71" r="1" fill="url(#gold)"/><path d="M${x} 73Q${x - 3.8} 78 ${x} 80Q${x + 3.8} 78 ${x} 73Z" fill="none" stroke="url(#gold)" stroke-width="1.15"/><circle cx="${x}" cy="78" r=".7" fill="#24727b"/>` :
    graphic ?
    `<circle cx="${x}" cy="71" r="1" fill="#c69a4c"/><ellipse cx="${x}" cy="74.2" rx="2.25" ry="3.3" fill="none" stroke="#ad7e35" stroke-width="1.4"/><path d="M${x - 1.1} 72Q${x - 2.4} 75 ${x} 76.8" fill="none" stroke="#f7d98d" stroke-width=".65"/>` :
    `<ellipse cx="${x}" cy="72.8" rx="2.1" ry="2.55" fill="url(#gold)" stroke="#93682e" stroke-width=".5"/><circle cx="${x - .5}" cy="72" r=".55" fill="#fff0bd"/>`}</g>`).join("");
  const glasses = accessory === 1 ? [64 - eyeSpacing, 64 + eyeSpacing].map(x =>
    `<ellipse cx="${x}" cy="59.5" rx="8.7" ry="7.1"/>`).join("") : [64 - eyeSpacing, 64 + eyeSpacing].map(x =>
    `<rect x="${x - 8.7}" y="53.5" width="17.4" height="12.7" rx="2.7"/>`).join("");
  const accessoryMarkup = accessory === 3 ? earrings : accessory === 1 || accessory === 2 ?
    `<g fill="#dbe8f3" fill-opacity=".06" stroke="${hairDark}" stroke-width="${graphic ? 1.8 : 1.5}">${glasses}<path d="M${72.7 - eyeSpacing} 58.4Q64 55.8 ${55.3 + eyeSpacing} 58.4M${63 - w} 56L${55.3 - eyeSpacing} 57M${72.7 + eyeSpacing} 57L${65 + w} 56" fill="none"/></g>` :
    accessory === 4 ? `<g fill="${dark}" opacity=".65">${[[44,70],[48,69],[51,72],[77,72],[80,69],[84,70]].map(([x,y]) =>
      `<circle cx="${x}" cy="${y}" r=".7"/>`).join("")}</g>` : "";
  const clothingStyle = Math.floor(n(17) * 2.99);
  const clothing = clothingStyle === 0 ?
    `<path d="M51 99Q64 110 77 99L80 102Q64 117 48 102Z" fill="${mix(shirt, "#172938", .4)}"/><path d="M51 100Q64 111 77 100" fill="none" stroke="${mix(shirt, "#f5dfbd", .27)}" stroke-width="1"/>` :
    clothingStyle === 1 ?
      `<path d="M49 99L58 109L64 105L70 109L79 99L86 104L76 116L64 108L52 116L42 104Z" fill="${mix(shirt, "#192932", .28)}"/><path d="M50 101L58 109M78 101L70 109" stroke="${mix(shirt, "#ffe8c7", .28)}" stroke-width="1"/><path d="M64 109V129" stroke="${mix(shirt, "#192932", .4)}" stroke-width="1"/>` :
      `<path d="M49 98L59 106L64 104L69 106L79 98L89 110L77 117L68 109L64 118L60 109L51 117L39 110Z" fill="${mix(shirt, "#1c2934", .25)}"/><path d="M59 108L57 121M69 108L71 121" stroke="${mix(shirt, "#f8e6cc", .45)}" stroke-width="1" stroke-linecap="round"/>`;
  const closeCrop = refined && !tailored;
  const silhouetteMask = tailored ? `<mask id="silhouette-edge" maskUnits="userSpaceOnUse" x="0" y="0" width="128" height="128" style="mask-type:alpha">${[
    [.55,0],[-.55,0],[0,.55],[0,-.55],[.39,.39],[-.39,.39],[.39,-.39],[-.39,-.39],
  ].map(([x,y]) => `<use href="#portrait-figure" x="${x}" y="${y}"/>`).join("")}</mask>` : "";
  const defs = `<clipPath id="tile"><rect x="${closeCrop ? 12 : 0}" y="${closeCrop ? 8 : 0}" width="${closeCrop ? 104 : 128}" height="${closeCrop ? 104 : 128}" rx="${closeCrop ? 14.6 : 18}"/></clipPath><clipPath id="head"><path d="${head}"/></clipPath><clipPath id="hair">${fronts[hairStyle]}</clipPath>${clips.join("")}
    <linearGradient id="bg" x2="1" y2="1"><stop stop-color="${mix(background, "#fff0d5", .12)}"/><stop offset="1" stop-color="${mix(background, "#39485d", .22)}"/></linearGradient>
    <radialGradient id="skin" gradientUnits="userSpaceOnUse" cx="48" cy="43" r="58"><stop stop-color="${light}"/><stop offset=".48" stop-color="${skin}"/><stop offset=".83" stop-color="${mix(skin, "#69413c", .2)}"/><stop offset="1" stop-color="${dark}"/></radialGradient>
    <linearGradient id="hair-fill" x1=".2" y1="0" x2=".8" y2="1"><stop stop-color="${hairLight}"/><stop offset=".3" stop-color="${hair}"/><stop offset="1" stop-color="${hairDark}"/></linearGradient>
    <linearGradient id="shirt" x2=".7" y2="1"><stop stop-color="${mix(shirt, "#f5dfc2", .15)}"/><stop offset=".5" stop-color="${shirt}"/><stop offset="1" stop-color="${mix(shirt, "#192333", .48)}"/></linearGradient>
    <linearGradient id="neck" x2=".2" y2="1"><stop stop-color="${dark}"/><stop offset=".32" stop-color="${mix(skin, "#6b423d", .25)}"/><stop offset="1" stop-color="${skin}"/></linearGradient>
    <linearGradient id="white" x2=".1" y2="1"><stop stop-color="#bdb6a9"/><stop offset=".5" stop-color="#eae4d7"/><stop offset="1" stop-color="#dcd6c8"/></linearGradient>
    <radialGradient id="warm"><stop stop-color="#c36555" stop-opacity=".2"/><stop offset="1" stop-color="#c36555" stop-opacity="0"/></radialGradient>
    <radialGradient id="bounce"><stop stop-color="${mix(skin, "#ffe9ca", .35)}" stop-opacity=".45"/><stop offset="1" stop-color="${light}" stop-opacity="0"/></radialGradient>
    <linearGradient id="gold" x2="1" y2=".6"><stop stop-color="#ffe8a6"/><stop offset=".35" stop-color="#d9ad54"/><stop offset=".65" stop-color="#9d702f"/><stop offset="1" stop-color="#eed28b"/></linearGradient>
    <radialGradient id="feather"><stop stop-color="#fff"/><stop offset=".55" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
    <mask id="soft-plane" maskUnits="userSpaceOnUse" x="30" y="30" width="68" height="68" style="mask-type:alpha"><ellipse cx="79" cy="64" rx="25" ry="31" fill="url(#feather)"/></mask>
    ${refined ? "" : `<filter id="grain" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="${state % 97}" result="noise"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".18"/></feComponentTransfer><feComposite in2="SourceGraphic" operator="in"/></filter>
    <filter id="organic" x="-.03" y="-.03" width="1.06" height="1.06" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency=".12" numOctaves="1" seed="${state % 71}" result="noise"/><feDisplacementMap in="SourceGraphic" in2="noise" scale=".35" xChannelSelector="R" yChannelSelector="G"/></filter>`}${silhouetteMask}`;
  const faceShading = graphic ? `<path d="M75 41Q92 64 78 82L66 ${bottom + 2}H104V34Z" fill="${dark}" opacity=".23"/>
    <path d="M39 64L48 71L57 72L50 77L39 74Z" fill="${light}" opacity=".45"/>
    <path d="M64 58L70 72L65 75L60 72Z" fill="${dark}" opacity=".27"/>` :
    `<path d="M77 35Q98 62 81 82L67 ${bottom + 3}L98 99V31Z" fill="${dark}" opacity=".35" mask="url(#soft-plane)"/>
    <ellipse cx="47" cy="71" rx="12" ry="9" fill="url(#warm)"/><ellipse cx="81" cy="72" rx="11" ry="9" fill="url(#warm)"/>
    <ellipse cx="53" cy="70" rx="10" ry="6" fill="url(#bounce)" opacity=".6"/>
    ${refined ? `<ellipse cx="68.3" cy="68.5" rx="3.1" ry="7" fill="${dark}" opacity=".1" mask="url(#soft-plane)"/><path d="M64 63Q64 68 62 71Q61.5 73 64 73.5" fill="none" stroke="${light}" stroke-width=".65" opacity=".42"/>` :
      `<path d="M66 54Q71 65 70 72L65 75L60 72Q64 66 66 54Z" fill="${dark}" opacity=".17"/>
    <path d="M63 61L62.5 69Q61 72 63 73" fill="none" stroke="${light}" stroke-width=".7" opacity=".6"/>`}
    <ellipse cx="61.5" cy="89.5" rx="8" ry="3" fill="url(#bounce)"/>`;
  const hairDetail = graphic ? `<g clip-path="url(#hair)" fill="none" stroke="${hairLight}" stroke-width="2.2" opacity=".4"><path d="${strand}"/></g>` :
    refined ? `<g clip-path="url(#hair)" fill="none" stroke-linecap="round"><path d="${strand}" stroke="${hairLight}" stroke-width=".8" opacity=".55"/><path d="${strand}" stroke="${hairDark}" stroke-width=".35" opacity=".3" transform="translate(1.7 2.3)"/></g>` :
    `<g clip-path="url(#hair)" fill="none" stroke-linecap="round" filter="url(#organic)">
      <path d="${strand}" stroke="${hairDark}" stroke-width="2.6" opacity=".24" transform="translate(1 1)"/>
      <path d="${strand}" stroke="${hairLight}" stroke-width="1.15" opacity=".76"/>
      <path d="${strand}" stroke="${mix(hair, "#f3dbb3", .43)}" stroke-width=".4" opacity=".65" transform="translate(-.65 -.6)"/>
      <path d="${strand}" stroke="${hairDark}" stroke-width=".5" opacity=".5" transform="translate(1.7 2.3)"/>
    </g>`;
  const contour = mix(skin, "#38292c", .38);
  const makeup = goth ? [64 - eyeSpacing, 64 + eyeSpacing].map(x =>
    `<g data-feature="smoky-eye"><path d="M${x - 9.3} 60Q${x - 9} 51 ${x} 52Q${x + 9} 52 ${x + 9.3} 60Q${x} 65 ${x - 9.3} 60Z" fill="#4a3049" opacity=".42"/>
      <path d="M${x - 8} 60Q${x} 51 ${x + 8} 60" fill="none" stroke="#352135" stroke-width="1.7" opacity=".7"/>
      <path d="M${x - 6} 61Q${x} 64 ${x + 6} 61" fill="none" stroke="#42263f" stroke-width=".85" opacity=".65"/></g>`).join("") : "";
  const eyeliner = goth ? [64 - eyeSpacing, 64 + eyeSpacing].map((x, i) => {
    const side = i ? 1 : -1;
    return `<path d="M${x + side * (eyeW - 1.6)} 58.6L${x + side * (eyeW + 2.7)} 56.8L${x + side * eyeW} 60Z" fill="#1b1323"/>`;
  }).join("") : "";
  const gothLips = `<path data-feature="dark-lipstick" d="M55 81Q59 78.4 62 80L64 81L66 79.8Q70 79 74 81.4Q70 86 64 85.7Q59 85.9 55 81Z" fill="${lip}" stroke="${mix(lip, "#211114", .5)}" stroke-width=".45"/><path d="M56.5 81.7Q64 83.5 72.7 81.6" fill="none" stroke="#2b1015" stroke-width=".6"/><path d="M60 84.4Q64 85 68 84" fill="none" stroke="${mix(lip, "#f7b2c3", .35)}" stroke-width=".45" opacity=".6"/>`;
  const lipContours = [
    "M55.2 81.7Q59.8 80.4 64 82Q69 81 73.8 80.3Q70.5 87 64.5 87.6Q58.8 87.3 55.2 81.7Z",
    "M53 80Q64 82.4 74.8 79.4Q73 90.2 64 90.3Q55 90 53 80Z",
    "M57.1 80.6Q64 77.3 70.9 80.8Q70.1 87.8 64 87.9Q58.6 87.8 57.1 80.6Z",
    "M55.7 82.1Q64.8 82.7 73.7 79Q74 81.8 70.4 84.4Q61.8 87.9 55.7 82.1Z",
    "M56.8 81.9Q60.7 78.9 64 80.6Q67.2 78.9 71.4 82.1Q65 86.9 56.8 81.9Z",
  ];
  const expression = friendlyWink ? 1 : mouthStyle;
  const mouth = friendlyWink ? mouths[1] : goth ? gothLips : mouths[mouthStyle];
  const mouthMarkup = kissWink
    ? `<g data-feature="kiss-lips" data-expression="kiss"><path data-feature="lipstick" d="M62 79Q65 78 67 80L69 81Q66 82 69 84L67 85Q64 87 62 84Q65 82 62 79Z" fill="${lip}" stroke="${mix(lip, deep, .2)}" stroke-width=".5"/><path d="M65 81.7L67 82.4" stroke="${deep}" stroke-width=".65"/><path data-feature="kiss-heart" d="M79 80C75 76 78 72 81 75C84 71 88 75 85 79L81 83Z" fill="#bb485a" stroke="#77363d" stroke-width=".4"/></g>`
    : hasLipstick
    ? `<g data-feature="lipstick" data-shade="${lip}">${goth && !friendlyWink ? mouth : `<path d="${lipContours[expression]}" fill="${lip}"/>${mouth}`}</g>`
    : mouth;
  const facialHairStyle = wardrobe?.facialHair || "none";
  let facialHairMarkup = "";
  if (facialHairStyle !== "none") {
    const color = mix(hair, "#28212a", .45);
    const mouthBottom = [88, 91, 88.5, 87.5, 87.5][expression];
    const mouthClearance = `M53 78H75Q78 78 78 82V${mouthBottom - 4}Q78 ${mouthBottom} 73 ${mouthBottom}H55Q50 ${mouthBottom} 50 ${mouthBottom - 4}V82Q50 78 53 78Z`;
    const jawHair = `M${64 - w + 1} 65Q45 74 53 77Q64 73 75 77Q83 74 ${64 + w - 1} 65L${64 + w + 2} ${bottom + 4}H${62 - w}Z`;
    const beardShape = facialHairStyle === "goatee"
      ? `M56 80Q64 77 72 80L74 88Q73 ${bottom + 1} 64 ${bottom + 2}Q55 ${bottom + 1} 54 88Z`
      : facialHairStyle === "boxed-beard" || facialHairStyle === "stubble"
        ? jawHair
        : facialHairStyle === "full-beard"
          ? `M${64 - w + 1} 65Q46 73 53 77Q64 73 75 77Q82 73 ${64 + w - 1} 65L88 78L85 87L78 94L72 ${bottom + 2}L64 ${bottom + 5}L56 ${bottom + 2}L50 94L43 87L40 78Z`
          : "";
    const moustache = facialHairStyle === "handlebar"
      ? "M64 78Q59 75.5 55 78.3C49 82 48 78 49 75C45 81 50 85 57 81L64 79.5L71 81C78 85 83 81 79 75C80 78 79 82 73 78.3Q69 75.5 64 78Z"
      : facialHairStyle === "chevron"
        ? "M52 79.4Q56 75.6 62 77.3L64 78.1L66 77.3Q72 75.6 76 79.4L73 81.1Q68 80.8 64 79.4Q60 80.8 55 81.1Z"
        : facialHairStyle === "stubble" ? ""
          : "M55 79Q59 76.8 63 78.2L64 78.8L65 78.2Q69 76.8 73 79L71 80.5Q67 80.3 64 79.5Q61 80.3 57 80.5Z";
    const texture = facialHairStyle === "stubble"
      ? `<g fill="none" stroke="${hairDark}" stroke-width=".65" stroke-linecap="round" opacity=".65" clip-path="url(#facial-hair-shape)">${[73,77,81,85,89,93].flatMap((y, row) =>
        [42,46,50,54,58,62,66,70,74,78,82,86].filter(x => x < 49 || x > 79 || y > 91)
          .map(x => `<path d="M${x + row % 2} ${y}l.4 1"/>`)).join("")}</g>`
      : beardShape ? `<path d="M48 82L50 87M54 91L57 94M63 92L64 ${bottom + 1}M74 90L72 94M80 82L78 87" fill="none" stroke="${hairLight}" stroke-width=".65" stroke-linecap="round" opacity=".3" clip-path="url(#facial-hair-shape)"/>` : "";
    const beard = beardShape ? `<defs><mask id="facial-hair-clearance" maskUnits="userSpaceOnUse" x="0" y="0" width="128" height="128"><rect width="128" height="128" fill="#fff"/><path d="${mouthClearance}" fill="#000"/></mask><clipPath id="facial-hair-shape"><path d="${beardShape}"/></clipPath></defs><g mask="url(#facial-hair-clearance)"${["boxed-beard", "stubble"].includes(facialHairStyle) ? ' clip-path="url(#head)"' : ""}><path data-feature="beard" d="${beardShape}"${facialHairStyle === "stubble" ? ' opacity=".24"' : ""}/>${texture}</g>` : "";
    facialHairMarkup = `<g data-feature="facial-hair" data-style="${facialHairStyle}" fill="${color}">${beard}${moustache ? `<path data-feature="moustache" d="${moustache}" stroke="${hairDark}" stroke-width=".35"/>` : ""}</g>`;
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="${closeCrop ? "12 8 104 104" : "0 0 128 128"}" data-avatar-version="study-v${version}"><defs>${defs}</defs>
    <g clip-path="url(#tile)"><rect width="128" height="128" fill="${graphic ? background : "url(#bg)"}"/>
      ${graphic ? `<path d="M0 0H82L16 128H0Z" fill="#fff0d6" opacity=".17"/>` :
        `<ellipse cx="34" cy="42" rx="58" ry="67" fill="#fff0d6" opacity=".13"/>`}${tailored ? avatarNamedBackdropMarkup(wardrobe) : ""}
      ${tailored ? '<g data-feature="silhouette-outline" opacity=".72"><rect width="128" height="128" fill="#000" mask="url(#silhouette-edge)"/></g><g id="portrait-figure">' : ""}<g transform="${pose}" fill="${graphic ? hairDark : "url(#hair-fill)"}" data-feature="hair-back">${rear}</g>
      ${tailored ? avatarWardrobeMarkup(wardrobe, shirt, skin, mix) : `<path d="M15 130L20 118Q23 106 48 100L55 97H73L80 100Q105 105 109 118L113 130Z" fill="${graphic ? shirt : "url(#shirt)"}"/>
      <path d="M53 85H75V100Q64 110 53 100Z" fill="${graphic ? skin : "url(#neck)"}"/>
      ${graphic ? `<path d="M53 88L75 91V96Q64 100 53 96Z" fill="${dark}" opacity=".5"/>` : ""}
      ${clothing}
      ${graphic ? "" : `<path d="M25 126Q26 113 40 110M100 128Q100 117 90 114" fill="none" stroke="${mix(shirt, "#f7e6cb", .3)}" stroke-width="1" opacity=".4"/><path d="M39 128L41 118M90 128L87 118" stroke="${mix(shirt, "#162a35", .4)}" stroke-width=".8" opacity=".6"/>`}`}
      <g transform="${pose}">
        <g data-feature="ears" fill="${graphic ? skin : "url(#skin)"}"${tailored ? ` stroke="${contour}" stroke-width=".5"` : ""}>${earX.map(x => `<ellipse cx="${x}" cy="63" rx="4" ry="8"/>`).join("")}</g>
        <g stroke="${dark}" stroke-width=".8" fill="none" opacity=".8">${earX.map(x => `<path d="M${x - 1} 60Q${x + 2.4} 57.5 ${x + 1} 63.5L${x} 67.5"/>`).join("")}</g>
        <path data-feature="head" d="${head}" fill="${graphic ? skin : "url(#skin)"}" ${graphic ? `stroke="${dark}" stroke-width=".85"` : tailored ? `stroke="${contour}" stroke-width=".65" stroke-linejoin="round"` : ""}/>
        <g clip-path="url(#head)">${faceShading}
          ${refined ? "" : `<path d="M34 44Q63 36 94 45L93 49Q62 42 35 50Z" fill="${deep}" opacity="${graphic ? ".12" : ".09"}"/>`}
        </g>
        <g data-feature="hair" fill="${graphic ? hair : "url(#hair-fill)"}"${tailored ? ` stroke="${hairDark}" stroke-width=".55" stroke-linejoin="round"` : ""}>${fronts[hairStyle]}</g>${hairDetail}
        ${hairStyle === 6 ? `<path d="M79 24C71 14 91 8 97 19C101 28 83 33 82 22Q82 15 92 19" fill="none" stroke="${hairLight}" stroke-width="${graphic ? 1.8 : 1}" opacity=".65"/>` : ""}
        <g data-feature="eyebrows" fill="${brow}">${eyebrows}</g>
        ${goth ? makeup : ""}<g data-feature="eyes">${eyes}</g>${goth ? eyeliner : ""}
        <path d="M60 72.8Q61 74.4 63 74.3M65.5 74.4Q67.5 74.5 69 72.7" fill="none" stroke="${dark}" stroke-width=".75" stroke-linecap="round" opacity=".8"/>
        <path d="M61.5 77L61 78.8M66.3 77L66.9 78.6" stroke="${dark}" stroke-width=".5" opacity=".4"/>${facialHairMarkup}
        <g data-feature="mouth"${kissWink ? ' data-expression="kiss"' : friendlyWink ? ' data-expression="smile"' : ""}>${mouthMarkup}</g>${butler ? `<g data-feature="mature-features" fill="none" stroke="${dark}" stroke-width=".55" opacity=".65"><path d="M49 44Q64 41 79 44M51 47Q64 45 77 47M40 60L36 58M40 62L36 63M88 60L92 58M88 62L92 63M52 74Q48 78 51 84M76 74Q80 78 77 84"/></g><path data-feature="moustache" d="M64 78Q59 75.5 55 80Q60 82 64 79.5Q68 82 73 80Q69 75.5 64 78Z" fill="#969891" stroke="#686d68" stroke-width=".45"/>` : ""}<g data-feature="accessory">${accessoryMarkup}</g>
      </g>${tailored ? "</g>" : ""}
      ${graphic || refined ? "" : '<rect width="128" height="128" fill="#fff" filter="url(#grain)" opacity=".3"/>'}
    </g></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}
