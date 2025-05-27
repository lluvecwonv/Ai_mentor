
/* 단과 대학 데이터 저장용 테이블 */

CREATE TABLE jbnu_college (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    UNIQUE (name)
);


/* 학과(부) 데이터 저장용 테이블 */

CREATE TABLE jbnu_department (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    college_id INT NOT NULL,
    FOREIGN KEY (college_id) REFERENCES jbnu_college(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (name)
);


/* 강의 데이터 저장용 테이블 */

CREATE TABLE jbnu_class (
    id INT AUTO_INCREMENT PRIMARY KEY,
    offered_year INT NOT NULL,
    semester INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    code INT NOT NULL,
    department_id INT NOT NULL,
    student_grade INT NOT NULL,
    schedule VARCHAR(255) NOT NULL,
    section INT NOT NULL,
    credits INT NOT NULL,
    is_mandatory_for_major VARCHAR(255) NOT NULL,
    professor VARCHAR(255) NOT NULL,
    delivery_mode VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    prerequisite TEXT NOT NULL,
    language VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    curriculum LONGTEXT NOT NULL,
    content LONGTEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES jbnu_department(id) ON DELETE CASCADE ON UPDATE CASCADE
);


/* */
