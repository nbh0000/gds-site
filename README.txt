GDS website prototype (KO/EN)

Open index.html in a modern browser. All images and scripts are local under /assets.

One page (index.html), anchor navigation:
회사소개 → 제품소개 (1.자동 이송형 경사계, 2.진동/소음 WAVEON 4 eco·geo, 3.RTK-GPS, 4.IOT 계측기, 5.모니터링 프로그램, 6.기타) → 개발용역 → 연락처 + 총판 광고 팝업 → 위치도

Content source: 홈페이지구성11.pdf. Only text, labels, images and specifications from that PDF are used.
Items the PDF lists by label only (WAVEON 시험성적서, RTK 특허/시험성적서, 판매처) are shown as labels; attach documents/links when available.

Admin (관리자 페이지)
- Run:   python admin_server.py        (serves the site + admin API on http://localhost:8765)
- Open:  http://localhost:8765/admin.html   initial password: gds1234  (change it in 설정)
- 콘텐츠 편집: every text on the landing page (KO/EN), link/map addresses. Saved to content.json; index.html loads it at runtime.
- 이미지: replace any image (upload to assets/ or type a path).
- 총판 문의: submissions from the popup form (index.html → 총판 광고 팝업) are stored in inquiries.json and listed here (read/unread, delete, CSV export).
- Without the server (plain static hosting) the site still works with default content, and the inquiry form falls back to e-mail.
- Do not publish admin_config.json / inquiries.json; admin_server.py already blocks direct access to them.
