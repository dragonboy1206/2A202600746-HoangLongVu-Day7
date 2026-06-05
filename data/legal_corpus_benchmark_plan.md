# Legal Corpus Benchmark Plan

## Selected document set

This benchmark plan is built around the five legal `.txt` files currently used as the main dataset for the lab.

| # | File | Type | Estimated domain | Characters |
|---|------|------|------------------|------------|
| 1 | `kehoach199.txt` | Plan | Public administration / anti-drug policy | 31210 |
| 2 | `luatchuyendoiso2025.txt` | Law | Digital transformation | 77318 |
| 3 | `luatthihanhandansu2025.txt` | Law | Civil judgment enforcement | 296562 |
| 4 | `nghidinh161-2026.txt` | Decree | Base salary and bonus policy | 17614 |
| 5 | `thongtu29-2026.txt` | Circular | Competitive electricity wholesale market | 106201 |

## Recommended domain statement for the report

Domain: Vietnamese legal and administrative documents.

Reason for choosing this domain:
The document set is long, structured, and fact-dense. It is suitable for retrieval benchmarking because users can ask exact questions about scope, target groups, effective dates, legal definitions, and responsibilities. The corpus also naturally benefits from metadata filtering by document type, year, and policy area.

## Recommended metadata schema

Use at least these metadata fields when building the document list:

| Metadata field | Type | Example | Why it helps retrieval |
|----------------|------|---------|------------------------|
| `doc_id` | string | `luatchuyendoiso2025` | Stable identifier for delete and traceability |
| `title` | string | `Luat Chuyen doi so` | Makes debugging and report writing easier |
| `doc_type` | string | `law`, `decree`, `circular`, `plan` | Useful for filtering legal source type |
| `topic` | string | `digital_transformation` | Helps narrow retrieval by subject |
| `year` | integer | `2025` | Useful when multiple versions exist |
| `language` | string | `vi` | Helpful for multilingual corpora |
| `source` | string | `data/luatchuyendoiso2025.txt` | Keeps provenance visible |

## Suggested metadata values

| File | `doc_type` | `topic` | `year` | `language` |
|------|------------|---------|--------|------------|
| `kehoach199.txt` | `plan` | `anti_drug_policy` | `2026` | `vi` |
| `luatchuyendoiso2025.txt` | `law` | `digital_transformation` | `2025` | `vi` |
| `luatthihanhandansu2025.txt` | `law` | `civil_enforcement` | `2025` | `vi` |
| `nghidinh161-2026.txt` | `decree` | `base_salary` | `2026` | `vi` |
| `thongtu29-2026.txt` | `circular` | `electricity_market` | `2026` | `vi` |

## Recommended chunking strategy

Primary strategy: `RecursiveChunker`

Why:
- Legal documents are long and heavily sectioned.
- They usually contain strong separators such as chapter headers, article markers, and numbered clauses.
- Recursive chunking tends to preserve article-level meaning better than fixed-size slicing.

Baseline comparisons:
- `FixedSizeChunker(chunk_size=500, overlap=50)`
- `SentenceChunker(max_sentences_per_chunk=3)`
- `RecursiveChunker(chunk_size=500)`

## Benchmark queries and gold answers

Use the same five queries across the group.

| # | Query | Gold answer |
|---|-------|-------------|
| 1 | Luat Chuyen doi so 2025 quy dinh pham vi dieu chinh nhu the nao? | Luat quy dinh ve chuyen doi so, bao gom nguyen tac, chinh sach, dieu phoi quoc gia, bien phap bao dam, Chinh phu so, kinh te so, xa hoi so, va trach nhiem cua co quan, to chuc, ca nhan trong chuyen doi so. |
| 2 | Nghi dinh 161/2026 quy dinh muc luong co so tu ngay nao va la bao nhieu? | Tu ngay 01/7/2026, muc luong co so la 2.530.000 dong/thang. |
| 3 | Thong tu 29/2026 dieu chinh nhung noi dung chinh nao cua thi truong ban buon dien canh tranh? | Thong tu quy dinh dang ky tham gia thi truong dien, lap ke hoach van hanh, co che chao gia, lap lich huy dong, do dem dien nang, xac dinh gia thi truong va thanh toan, cong bo thong tin, giam sat van hanh, va trach nhiem cua cac don vi tham gia thi truong dien. |
| 4 | Luat Thi hanh an dan su 2025 quy dinh ai co tham quyen giai quyet khieu nai lan hai? | Thu truong co quan quan ly thi hanh an dan su thuoc Bo Tu phap giai quyet khieu nai lan hai doi voi quyet dinh giai quyet khieu nai chua co hieu luc thi hanh cua Thu truong co quan thi hanh an dan su tinh, thanh pho va cua Truong van phong thi hanh an dan su. |
| 5 | Ke hoach 199/KH-UBND nam 2026 huong toi muc tieu tong quat nao? | Huy dong suc manh tong hop cua he thong chinh tri va toan dan tham gia phong, chong toi pham va te nan ma tuy; tung buoc xay dung va duy tri ben vung xa, phuong khong ma tuy trong giai doan 2026-2030, huong toi xay dung tinh khong ma tuy. |

## Suggested filter query for the demo

Use this as the metadata-filter example:

Query: `Muc luong co so tu ngay 01/7/2026 la bao nhieu?`

Filter:

```python
{"doc_type": "decree", "topic": "base_salary"}
```

Reason:
Without filtering, similar legal phrases such as `pham vi dieu chinh` or `doi tuong ap dung` may appear in many documents. Filtering lets the store search only the decree that actually discusses salary policy.

## Expected failure case

Potential failure:
The query `Ai co tham quyen giai quyet khieu nai?` may retrieve the wrong part of `luatthihanhandansu2025.txt` because that document contains many nearby articles about complaint rights, complaint procedures, and complaint authority.

Why it may fail:
- The law is very long.
- Many chunks share similar legal vocabulary.
- Small chunks may separate the article title from its detailed clause.

Suggested improvement:
- Increase chunk overlap.
- Add article markers to metadata if you extend preprocessing later.
- Use metadata filtering by `topic` and `doc_type`.

## Recommended next lab actions

1. Implement the TODOs in `src/chunking.py`, `src/store.py`, and `src/agent.py`.
2. Create `Document(...)` entries for the five legal files with the metadata above.
3. Run `ChunkingStrategyComparator().compare()` on at least two of the longer files.
4. Store the five benchmark queries and their retrieved top-3 chunks in the report.
5. Record at least one failure case where legal sections with similar wording confuse retrieval.
