# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Vũ  
**Nhóm:** [Điền tên nhóm]  
**Ngày:** 2026-06-05

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**  
High cosine similarity cho thấy hai vector embedding có hướng gần nhau, nghĩa là hai đoạn văn bản có ý nghĩa hoặc chủ đề tương đối giống nhau. Trong bài toán text, điều này thường có nghĩa là nội dung của hai câu đề cập đến cùng một vấn đề hoặc các khái niệm liên quan.

**Ví dụ HIGH similarity:**
- Sentence A: Chuyển đổi số giúp nâng cao hiệu quả quản trị.
- Sentence B: Chuyển đổi số tạo ra giá trị mới và minh bạch hơn.
- Tại sao tương đồng: Cả hai câu đều nói về lợi ích và tác động của chuyển đổi số.

**Ví dụ LOW similarity:**
- Sentence A: Mức lương cơ sở được áp dụng từ ngày 01/7/2026.
- Sentence B: Thị trường bán buôn điện cạnh tranh có cơ chế chào giá.
- Tại sao khác: Hai câu thuộc hai lĩnh vực pháp lý khác nhau và không chia sẻ nhiều ngữ cảnh.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**  
Cosine similarity tập trung vào hướng của vector, phù hợp hơn với text embeddings vì ý nghĩa thường thể hiện qua hướng thay vì độ lớn tuyệt đối. Euclidean distance dễ bị ảnh hưởng bởi độ lớn vector hơn, trong khi điều cần so sánh với text là mức độ giống nhau về mặt nghĩa.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

Trình bày phép tính:

`num_chunks = ceil((doc_length - overlap) / (chunk_size - overlap))`

`= ceil((10000 - 50) / (500 - 50))`

`= ceil(9950 / 450)`

`= ceil(22.11)`

`= 23`

**Đáp án:** 23 chunks

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**  
Khi overlap = 100 thì số chunk là `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 25`. Overlap lớn hơn tạo nhiều chunk hơn nhưng giữ được ngữ cảnh ở ranh giới giữa các chunk, giúp retrieval ít bị mất thông tin quan trọng.

---

## 2. Document Selection - Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Văn bản pháp lý và hành chính tiếng Việt

**Tại sao nhóm chọn domain này?**  
Nhóm chọn bộ tài liệu pháp lý vì nội dung dài, cấu trúc rõ ràng theo chương, điều, khoản, và có nhiều thông tin có thể truy vấn chính xác. Đây cũng là domain giúp nhóm nhìn ra rất rõ ưu và nhược điểm của từng chiến lược chunking: chiến lược cơ học như `FixedSizeChunker`, chiến lược ngữ nghĩa theo câu, chiến lược đệ quy tổng quát, chiến lược bám cấu trúc luật, và chiến lược kết hợp nhiều nguồn chunk.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | `kehoach199.txt` | `data/kehoach199.txt` | 31210 | `doc_id`, `title`, `doc_type=plan`, `topic=anti_drug_policy`, `year=2026`, `language=vi`, `source` |
| 2 | `luatchuyendoiso2025.txt` | `data/luatchuyendoiso2025.txt` | 77318 | `doc_id`, `title`, `doc_type=law`, `topic=digital_transformation`, `year=2025`, `language=vi`, `source` |
| 3 | `luatthihanhandansu2025.txt` | `data/luatthihanhandansu2025.txt` | 296562 | `doc_id`, `title`, `doc_type=law`, `topic=civil_enforcement`, `year=2025`, `language=vi`, `source` |
| 4 | `nghidinh161-2026.txt` | `data/nghidinh161-2026.txt` | 17614 | `doc_id`, `title`, `doc_type=decree`, `topic=base_salary`, `year=2026`, `language=vi`, `source` |
| 5 | `thongtu29-2026.txt` | `data/thongtu29-2026.txt` | 106201 | `doc_id`, `title`, `doc_type=circular`, `topic=electricity_market`, `year=2026`, `language=vi`, `source` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `luatchuyendoiso2025` | Dùng để truy vết tài liệu, delete document, và kiểm tra kết quả retrieval |
| `doc_type` | string | `law`, `decree`, `plan` | Hỗ trợ filter theo loại văn bản pháp lý |
| `topic` | string | `digital_transformation` | Giảm nhiễu khi truy vấn theo chủ đề |
| `year` | int | `2025` | Hữu ích khi có nhiều phiên bản văn bản qua các năm |
| `language` | string | `vi` | Hữu ích nếu sau này mở rộng sang corpus song ngữ |
| `source` | string | `data/luatchuyendoiso2025.txt` | Giúp truy vết nguồn và viết report rõ ràng |

---

## 3. Chunking Strategy - Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu đại diện với `chunk_size=500`:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| `kehoach199.txt` | `fixed_size` | 53 | 494.92 | Trung bình, dễ cắt ngang ý |
| `kehoach199.txt` | `by_sentences` | 38 | 619.16 | Tốt theo câu, nhưng có chunk dài |
| `kehoach199.txt` | `recursive` | 74 | 317.36 | Tốt, giữ được ranh giới nội dung |
| `luatchuyendoiso2025.txt` | `fixed_size` | 127 | 499.57 | Trung bình |
| `luatchuyendoiso2025.txt` | `by_sentences` | 164 | 346.09 | Khá tốt với văn bản giải thích |
| `luatchuyendoiso2025.txt` | `recursive` | 146 | 389.36 | Tốt cho văn bản có cấu trúc điều khoản |
| `nghidinh161-2026.txt` | `fixed_size` | 30 | 486.57 | Trung bình |
| `nghidinh161-2026.txt` | `by_sentences` | 20 | 654.90 | Dễ tạo chunk quá dài |
| `nghidinh161-2026.txt` | `recursive` | 40 | 326.57 | Tốt hơn cho truy vấn chính xác |

### Strategy Của Tôi

**Loại:** `EnsembleChunker`

**Mô tả cách hoạt động:**  
`EnsembleChunker` là chiến lược kết hợp nhiều cách chia chunk thay vì chỉ dùng một cách duy nhất. Cụ thể, tôi kết hợp `SentenceChunker`, `LegalChunker`, và `RecursiveChunker`, sau đó loại bỏ các chunk trùng lặp để giữ lại tập chunk đa dạng nhưng không bị dư thừa quá mức.

**Tại sao tôi chọn strategy này cho domain nhóm?**  
Tôi chọn `EnsembleChunker` vì bộ tài liệu pháp lý có cả cấu trúc hình thức rất rõ và các câu chứa thông tin ngắn, quan trọng. Kết hợp nhiều chiến lược giúp hệ thống vừa giữ được ranh giới pháp lý như điều, khoản, vừa không bỏ lỡ các chunk ngắn có độ khớp từ khóa cao.

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| `luatchuyendoiso2025.txt` | best baseline: `SentenceChunker` | 164 | 346.09 | Khá tốt cho nội dung giải thích |
| `luatchuyendoiso2025.txt` | **của tôi: `EnsembleChunker`** | Nhiều hơn baseline | Linh hoạt | Bao phủ tốt cả ngữ nghĩa và cấu trúc |
| `nghidinh161-2026.txt` | best baseline: `FixedSizeChunker` | 30 | 486.57 | Đơn giản, dễ triển khai |
| `nghidinh161-2026.txt` | **của tôi: `EnsembleChunker`** | Nhiều hơn baseline | Linh hoạt | Tăng cơ hội bắt đúng điều khoản quan trọng |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | `EnsembleChunker` | 9 | Kết hợp ngữ nghĩa, cấu trúc pháp lý, và rerank từ khóa | Số chunk lớn, chi phí xử lý cao hơn |
| Tiến | `FixedSizeChunker` | 6 | Baseline rõ ràng, dễ cài đặt và dễ giải thích | Precision thấp hơn, dễ bị flooding bởi tài liệu lớn |
| Minh | `RecursiveChunker` | 8 | Cân bằng tốt giữa độ dài chunk và mạch nội dung | Vẫn thua strategy kết hợp ở các query khó |
| Yến | `Legal-Structure Recursive` | 8 | Rất hợp domain pháp lý, giữ được Điều/Khoản | Cần tinh chỉnh thêm để xử lý các điều quá dài và benchmark chi tiết |
| Sơn | `HybridLegalChunker` | 9.5 | Kết hợp tốt cấu trúc pháp lý với metadata filtering | Số chunk tăng và cần thêm bước tiền xử lý header/boilerplate |

**Strategy nào tốt nhất cho domain này? Tại sao?**  
Trong phần thực nghiệm cá nhân sau khi nâng cấp pipeline, `EnsembleChunker` là lựa chọn tốt nhất vì nó tận dụng đồng thời lợi ích của chunk theo câu, chunk theo cấu trúc pháp lý, và chunk đệ quy. Khi kết hợp thêm cơ chế rerank theo từ khóa, cấu hình này đạt `Hit@3 = 5/5` trên bộ benchmark hiện tại.

### Kết Quả So Sánh Strategy Trong Phase 2

Chạy bằng lệnh:

```text
python main.py --benchmark fixed
python main.py --benchmark sentence
python main.py --benchmark recursive
```

| Strategy | Số chunk tạo ra | Hit@3 trên 5 benchmark queries | Nhận xét |
|----------|------------------|-------------------------------|----------|
| `FixedSizeChunker` | 875 | 5 / 5 | Hiệu quả hơn sau khi có rerank từ khóa |
| `SentenceChunker` | 828 | 5 / 5 | Ổn định, dễ đọc, mạnh ở mức câu |
| `RecursiveChunker` | 1071 | 5 / 5 | Bao phủ tốt các đoạn dài |
| `LegalChunker` | 1141 | 5 / 5 | Hợp cấu trúc pháp lý |
| `HybridLegalChunker` | 1629 | 5 / 5 | Giữ được chi tiết nhưng nhiều chunk |
| `EnsembleChunker` | 2632 | 5 / 5 | Cấu hình mạnh nhất và linh hoạt nhất |

### Tổng Hợp Kết Quả Trong Nhóm

| Thành viên | Chiến lược chính | Embedding / Search setup | Hit@3 | Điểm mạnh nổi bật | Query / điểm yếu chính |
|-----------|-------------------|--------------------------|-------|-------------------|------------------------|
| Tiến | `FixedSizeChunker` | `mock embeddings fallback`, search thường | 3 / 5 | Baseline rõ ràng, dễ so sánh, dễ kiểm soát `chunk_size` và `overlap` | Trượt Q2 và Q5; dễ bị flooding bởi `luatthihanhandansu2025` |
| Minh | `RecursiveChunker` | In-memory store, chunk theo separator ưu tiên | 4 / 5 | Giữ ranh giới đoạn/câu tốt hơn baseline, cân bằng giữa độ dài và ngữ nghĩa | Vẫn lỗi ở query liên quan `nghidinh161`; chưa đủ mạnh ở passage-level retrieval |
| Yến | `Legal-Structure Chunking` | `RecursiveChunker` với separator theo `Điều`, `Khoản` | Chưa ghi đủ bảng benchmark trong file cá nhân | Rất sát domain pháp lý, giữ trọn khối nghĩa của điều khoản | Cần benchmark chi tiết hơn để so sánh định lượng với các chiến lược khác |
| Sơn | `HybridLegalChunker` | `all-MiniLM-L6-v2` + `search_with_filter(doc_id=...)` | 5 / 5 | Kết hợp chunk theo cấu trúc pháp lý với metadata filtering; agent answer đúng 5/5 | Top-1 đôi lúc vẫn dính header/boilerplate; cần tiền xử lý văn bản sạch hơn |
| Vũ | `EnsembleChunker` | `mock embeddings fallback` + lexical rerank + nhiều nguồn chunk | 5 / 5 | Kết hợp `Sentence`, `Legal`, `Recursive`; top-3 ổn định và bao phủ tốt | Số chunk lớn nhất, chi phí xử lý cao hơn |

| Tiêu chí so sánh | Tiến | Minh | Yến | Sơn | Vũ |
|------------------|------|------|-----|-----|-----|
| Mục tiêu chính | Baseline | Cân bằng tổng quát | Bám cấu trúc luật | Tối ưu theo cấu trúc + filter | Kết hợp nhiều chiến lược + rerank |
| Kiểu chunking | Cắt theo kích thước cố định | Đệ quy theo separator | Đệ quy theo `Điều/Khoản` | Lai giữa pháp lý và recursive | Hợp nhất sentence + legal + recursive |
| Mức độ phức tạp | Thấp | Trung bình | Trung bình | Cao | Cao |
| Khả năng giữ ngữ cảnh | Thấp đến trung bình | Tốt | Tốt | Rất tốt | Rất tốt |
| Phù hợp với domain pháp lý | Thấp | Khá | Cao | Rất cao | Rất cao |

Từ các bài cá nhân, nhóm có thể rút ra một xu hướng khá rõ: khi đi từ chiến lược cơ học sang chiến lược có awareness về cấu trúc pháp lý, chất lượng retrieval tăng lên đáng kể. `FixedSizeChunker` phù hợp làm baseline để nhìn ra nhược điểm của việc cắt cứng; `RecursiveChunker` và `Legal-Structure Chunking` giúp giữ ngữ cảnh tốt hơn; còn các cấu hình nâng cao như `HybridLegalChunker` của Sơn và `EnsembleChunker` của tôi cho thấy khi kết hợp chunking với metadata filtering hoặc lexical rerank thì kết quả ổn định hơn hẳn.

Nếu xét theo mức độ hoàn thiện của pipeline trên bộ benchmark hiện tại, hai hướng mạnh nhất trong nhóm là:
- `HybridLegalChunker` + `all-MiniLM-L6-v2` + `search_with_filter` của **Sơn**
- `EnsembleChunker` + lexical rerank của **Vũ**

Hai cấu hình này đạt cùng `Hit@3 = 5/5`, nhưng khác nhau ở triết lý:
- Bài của **Sơn** mạnh ở việc dùng embedding thực hơn và filter metadata rất chặt theo `doc_id`.
- Bài của **tôi** mạnh ở việc cải thiện retrieval ngay cả khi vẫn dùng mock embeddings, bằng cách tăng chất lượng chunk và thêm lexical rerank.

---

## 4. My Approach - Cá nhân (10 điểm)

Giải thích cách tiếp cận của tôi khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** - approach:  
Tôi dùng regex để tách câu dựa trên dấu câu như `.`, `!`, `?` kết hợp khoảng trắng hoặc xuống dòng. Sau đó tôi gom lại thành từng nhóm tối đa `max_sentences_per_chunk` câu để tạo chunk, đồng thời bỏ qua các phần rỗng.

**`RecursiveChunker.chunk` / `_split`** - approach:  
Tôi thiết kế base case là trả về ngay nếu text rỗng, ngắn hơn `chunk_size`, hoặc fallback sang `FixedSizeChunker` nếu không còn separator phù hợp. Ở mỗi mức đệ quy, tôi thử ghép các mảnh văn bản nhỏ theo separator hiện tại, nếu vượt quá ngưỡng thì đẩy phần đó xuống separator tiếp theo.

**`EnsembleChunker`** - approach:  
Tôi kết hợp kết quả từ `SentenceChunker`, `LegalChunker`, và `RecursiveChunker`, sau đó chuẩn hóa và loại bỏ chunk trùng lặp. Mục tiêu là tạo ra một tập chunk phong phú hơn, vừa có độ bám ngữ nghĩa tốt vừa có độ bám cấu trúc pháp lý tốt.

### EmbeddingStore

**`add_documents` + `search`** - approach:  
Tôi sử dụng in-memory store là một danh sách record chuẩn hóa gồm `id`, `content`, `metadata`, `embedding`. Khi search, tôi không chỉ dùng dot product của embedding mà còn cộng thêm điểm lexical overlap giữa query và nội dung chunk để rerank kết quả tốt hơn.

**`search_with_filter` + `delete_document`** - approach:  
Tôi filter trước theo metadata rồi mới tính độ tương đồng trên tập bản ghi đã lọc, cách này giúp giảm nhiễu. Khi delete, tôi xóa tất cả record có `metadata["doc_id"]` trùng với `doc_id` cần xóa và trả về `True/False` để biết có xóa được hay không.

### KnowledgeBaseAgent

**`answer`** - approach:  
Tôi retrieve top-k chunk từ store, ghép chúng thành một phần `Context`, sau đó tạo prompt yêu cầu model chỉ trả lời dựa trên context được cung cấp. Cách này giữ đúng form cơ bản của RAG: retrieve trước, generate sau.

### Test Results

```text
python -m pytest tests/ -v
42 passed in 0.08s
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions - Cá nhân (5 điểm)

Sử dụng `compute_similarity(_mock_embed(a), _mock_embed(b))` trên 5 cặp câu:

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Chuyển đổi số giúp nâng cao hiệu quả quản trị. | Chuyển đổi số tạo ra giá trị mới và minh bạch hơn. | high | -0.0912 | Không |
| 2 | Mức lương cơ sở được áp dụng từ ngày 01/7/2026. | Từ ngày 01/7/2026 mức lương cơ sở là 2.530.000 đồng/tháng. | high | 0.0317 | Một phần |
| 3 | Thị trường bán buôn điện cạnh tranh có cơ chế chào giá. | Vận hành thị trường điện bao gồm công bố thông tin và giám sát. | high | 0.0943 | Gần đúng |
| 4 | Chuyển đổi số là quá trình dựa trên công nghệ số. | Tối nay tôi muốn ăn bún chả ở Hà Nội. | low | -0.0352 | Đúng |
| 5 | Thi hành án dân sự quy định quyền khiếu nại. | Mức lương cơ sở áp dụng cho cán bộ công chức viên chức. | low | -0.1020 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**  
Cặp 1 bất ngờ nhất vì về mặt ý nghĩa hai câu khá gần nhau nhưng điểm lại âm. Nguyên nhân là project đang dùng `MockEmbedder` mang tính xác định để test pipeline, không phải embedding model học nghĩa thật, nên score này phản ánh giới hạn của backend mock hơn là chất lượng của hàm cosine similarity.

---

## 6. Results - Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân. Ở giai đoạn này, `EmbeddingStore` đang lưu mỗi tài liệu thành một record lớn và dùng `MockEmbedder`, vì vậy kết quả retrieval được dùng để phân tích limitation của pipeline hiện tại.

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Luật Chuyển đổi số 2025 quy định phạm vi điều chỉnh như thế nào? | Luật quy định về chuyển đổi số, bao gồm nguyên tắc, chính sách, điều phối quốc gia, biện pháp bảo đảm, Chính phủ số, kinh tế số, xã hội số, và trách nhiệm của cơ quan, tổ chức, cá nhân trong chuyển đổi số. |
| 2 | Nghị định 161/2026 quy định mức lương cơ sở từ ngày nào và là bao nhiêu? | Từ ngày 01/7/2026, mức lương cơ sở là 2.530.000 đồng/tháng. |
| 3 | Thông tư 29/2026 điều chỉnh những nội dung chính nào của thị trường bán buôn điện cạnh tranh? | Thông tư quy định đăng ký tham gia thị trường điện, lập kế hoạch vận hành, cơ chế chào giá, lập lịch huy động, đo đếm điện năng, xác định giá thị trường và thanh toán, công bố thông tin, giám sát vận hành, và trách nhiệm của các đơn vị tham gia thị trường điện. |
| 4 | Luật Thi hành án dân sự 2025 quy định ai có thẩm quyền giải quyết khiếu nại lần hai? | Thủ trưởng cơ quan quản lý thi hành án dân sự thuộc Bộ Tư pháp giải quyết khiếu nại lần hai đối với quyết định giải quyết khiếu nại chưa có hiệu lực thi hành của Thủ trưởng cơ quan thi hành án dân sự tỉnh, thành phố và của Trưởng văn phòng thi hành án dân sự. |
| 5 | Kế hoạch 199/KH-UBND năm 2026 hướng tới mục tiêu tổng quát nào? | Huy động sức mạnh tổng hợp của hệ thống chính trị và toàn dân tham gia phòng, chống tội phạm và tệ nạn ma túy; từng bước xây dựng và duy trì bền vững xã, phường không ma túy trong giai đoạn 2026-2030, hướng tới xây dựng tỉnh không ma túy. |

### Kết Quả Của Tôi

Sau khi nâng cấp benchmark theo chunk ở Phase 2, tôi chọn `EnsembleChunker` làm cấu hình chính thức để tổng hợp kết quả dưới đây.

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Phạm vi điều chỉnh của Luật Chuyển đổi số 2025 | Trả về chunk của `luatchuyendoiso2025`, thuộc phần điều khoản về chuyển đổi số | 0.5540 | Có | Agent trả về câu trả lời mẫu dựa trên context |
| 2 | Mức lương cơ sở từ ngày nào và bao nhiêu | Trả về chunk của `nghidinh161-2026`, có mốc hiệu lực và quy định lương cơ sở | 0.5130 | Có | Agent trả về câu trả lời mẫu dựa trên context |
| 3 | Nội dung chính của Thông tư 29/2026 | Trả về đúng chunk của `thongtu29-2026`, thuộc Điều 1 phạm vi điều chỉnh | 0.5310 | Có | Agent trả về câu trả lời mẫu dựa trên context |
| 4 | Thẩm quyền giải quyết khiếu nại lần hai | Trả về chunk của `luatthihanhandansu2025`, đúng nhóm nội dung khiếu nại | 0.6500 | Có | Agent trả về câu trả lời mẫu dựa trên context |
| 5 | Mục tiêu tổng quát của Kế hoạch 199/KH-UBND | Trả về đúng chunk của `kehoach199` | 0.4060 | Có | Agent trả về câu trả lời mẫu dựa trên context |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5 với `EnsembleChunker`

**Nhận xét:**  
Kết quả này cho thấy chất lượng retrieval cải thiện rõ rệt khi kết hợp nhiều chiến lược chunking và thêm lexical rerank. Dù hệ thống vẫn đang dùng `MockEmbedder`, việc bổ sung điểm khớp từ khóa đã giúp top-3 ổn định hơn và đạt kết quả đầy đủ trên bộ benchmark hiện tại.

---

## 7. What I Learned (5 điểm - Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**  
Điều tôi học được rõ nhất từ các thành viên trong nhóm là mỗi chiến lược chunking phản ánh một cách nhìn rất khác về cùng một bộ tài liệu. Từ bài của Tiến, tôi thấy baseline `FixedSizeChunker` rất hữu ích để chứng minh vì sao cắt cơ học là chưa đủ cho dữ liệu pháp lý. Từ bài của Minh, tôi học được cách dùng `RecursiveChunker` như một giải pháp cân bằng và dễ mở rộng. Từ bài của Yến, tôi học được rằng với luật và nghị định, việc bám vào mốc `Điều` và `Khoản` là cực kỳ quan trọng nếu muốn giữ nghĩa pháp lý trọn vẹn. Từ bài của Sơn, tôi học được giá trị rất lớn của việc kết hợp chunking phù hợp domain với `metadata filtering` và embedding model thực tế thay vì chỉ trông vào mock embeddings.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**  
Qua phần tổng hợp và so sánh, tôi nhận ra bài toán retrieval không chỉ phụ thuộc vào chunking mà còn phụ thuộc rất mạnh vào metadata, preprocessing và bước xếp hạng lại kết quả. Bài học quan trọng mà tôi rút ra cho phần demo là phải trình bày rõ sự khác nhau giữa document-level hit và passage-level hit, vì đây là điểm quyết định chất lượng thật của hệ thống RAG; đồng thời cần chỉ ra khi nào `metadata filtering` hoặc `lexical rerank` giúp hệ thống tiến từ “đúng tài liệu” sang “đúng đoạn”.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**  
Nếu làm lại, tôi sẽ tiếp tục giữ hướng kết hợp nhiều chiến lược nhưng sẽ tối ưu sâu hơn cho từng loại văn bản, ví dụ tách riêng pipeline cho luật, nghị định, thông tư, và kế hoạch. Tôi cũng sẽ thay `MockEmbedder` bằng local embedder hoặc OpenAI embedder để điểm similarity phản ánh nghĩa tốt hơn, đồng thời bổ sung metadata chi tiết hơn như `chapter`, `article`, `issuing_body`, và `effective_date`.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 9 / 10 |
| Chunking strategy | Nhóm | 13 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 8 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **84 / 100** |
