# Rules

The rule table. Code reads these files; nothing here is hard-coded in Python.

```
funding.json        USG funding guidelines
events.json         Trojan Event Services terms, FAQ and Student Handbook event policy
outside_money.json  sponsorship, donations, fundraising, raffles
recognition.json    constitution template clauses and recognition requirements
calendar.json       academic calendar dates used by the deadline calculator
sources/            snapshots of the official documents, each with its fetch date
```

Every rule must have:

| Field | Meaning |
|---|---|
| `id` | stable identifier |
| `owner_office` | who owns the rule |
| `source`, `source_url` | document and link |
| `source_text` | the exact paragraph from the snapshot |
| `effective_date` | date of the document version |
| `verified` | `read`, `fetched` or `unverified` |
| `severity` | `red`, `yellow` or `office_decides` |
| `message`, `fix_template` | what the officer sees |

A rule missing any of these does not load. A rule marked `unverified` is always shown yellow.

The list of rules and their sources is in [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) section 7 and [docs/research/club_platform.md](../docs/research/club_platform.md).

A person reviews every rule against its source before it is used.
