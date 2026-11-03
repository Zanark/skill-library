# Evidence receipt <stable ID>

Date/time and timezone: `<actual observed time>`  
Purpose/criterion: `<what outcome this supports>`  
Authority and allowed scope: `<local/task boundary>`

| Item | Actual value |
|---|---|
| Input/source and revision | <path, role, revision/hash where relevant> |
| Environment | <fixture/local/target machine; relevant versions> |
| Action/command | <actual invocation, redacted safely> |
| Result | <observed exit/result, not expected result> |
| Artifact | <full absolute path, type, size/hash if relevant> |
| Inspection | <what was actually read/viewed/exercised> |
| Limitations | <unverified behavior, partial scope, stale input> |
| Human acceptance | <not requested/pending/explicit artifact approval> |
| Publication | <local only or exact verified remote state> |

Inference supported: `<narrow conclusion>`  
Not established: `<for example semantic correctness, target qualification, rights>`

Keep confidential inputs/identifiers in an authorized private receipt, not a
public repository. A checksum proves bytes, not correctness or clearance.
