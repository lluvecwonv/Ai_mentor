
/* 툴 리스트 저장할 테이블 */

CREATE TABLE jbnu_tool_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tool_name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    api_url VARCHAR(255) NOT NULL,
    api_body TEXT NOT NULL
);
