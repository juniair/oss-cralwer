import psycopg2

#Sever
#DB 생성을 별도로 작업 후 실행해야함
#conn_string = "host='localhost' dbname = 'crawler' user = 'postgres' password = '1234'"


#Local
conn_string = "host='localhost' dbname = 'crawler' user = 'postgres' password = '12345678' port = '15432'"

conn = psycopg2.connect(conn_string)
cur = conn.cursor()
cur.execute("""CREATE TABLE dpa_crawler_tb (
                   CRAWLER_NAME    TEXT         NOT NULL    PRIMARY KEY,
                   CRAWLER_STATUS  TEXT         NOT NULL,
                   UPDATE_TIME     TIMESTAMP    NOT NULL
           );""")

cur.execute("COMMENT ON TABLE dpa_crawler_tb IS '크롤러';")
cur.execute("COMMENT ON COLUMN dpa_crawler_tb.crawler_name IS '크롤러명';")
cur.execute("COMMENT ON COLUMN dpa_crawler_tb.crawler_status IS '크롤러상태';")
cur.execute("COMMENT ON COLUMN dpa_crawler_tb.update_time IS '갱신시각';")

cur.execute("CREATE SEQUENCE seq_pid START 1;")
cur.execute("CREATE SEQUENCE seq_reid START 1;")
# 19.09.18 PROJECT_FIEL_DB의 컬럼정보를 굳이 불리할 필요 없다고 생각되서 PROJECT_VER 컬럼을 PROJECT_DB에 합침
# 기존의 PROJECT_FILE_DB의 명칭은 그대로 사용하며 크롤러명/프로젝트명/RELEASE_VERSION/소스파일로
# 이어지는 PATH정보 중 RELEASE_VERSION/ 까지 가지고 있고 해당경로와 RELEASE_ID를 매칭되게 수정
cur.execute("""CREATE TABLE dpa_crawler_project_tb (
                   PID          INT   DEFAULT nextval('seq_pid')    PRIMARY KEY,
				   PROJECT_NAME    TEXT    NOT NULL,
                   CRAWLER_NAME    TEXT    NOT NULL     REFERENCES DPA_CRAWLER_TB (crawler_name),
                   PROJECT_URL     TEXT,
                   SUMMARY         TEXT,
                   HOMEPAGE_URL    TEXT,
                   CREATED_DT      DATE,
                   CATEGORY        TEXT,
                   LICENSE         TEXT,
                   PROGRAMMING_LANG    TEXT,
                   PROJECT_VER     TEXT,
                   CONSTRAINT project_tb_project_name_key UNIQUE (project_name, crawler_name, project_url)
           );""")

cur.execute("COMMENT ON TABLE dpa_crawler_project_tb IS '크롤러프로젝트';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.pid IS '프로젝트ID';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.project_name IS '프로젝트명';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.crawler_name IS '크롤러명';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.project_url IS '프로젝트URL';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.summary IS '요약설명';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.homepage_url IS '홈페이지URL';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.created_dt IS '등록일';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.category IS '카테고리';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.license IS '라이선스';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.programming_lang IS '개발언어';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_tb.project_ver IS '프로젝트버전';")

cur.execute("""CREATE TABLE dpa_crawler_release_tb (
                   RELEASE_ID      INT  DEFAULT nextval('seq_reid')     PRIMARY KEY,
                   PID             INT  NOT NULL    REFERENCES DPA_CRAWLER_PROJECT_TB (pid),
                   RELEASE_VER     TEXT NOT NULL,
                   FILE_DIR        TEXT,
                   RELEASE_DT      DATE,
                   DOWNLOAD_DT     DATE,
                   HASHING         TEXT,
                   CONSTRAINT project_file_tb_pkey UNIQUE (pid, RELEASE_VER)
           );""")

cur.execute("COMMENT ON TABLE dpa_crawler_release_tb IS '크롤러프로젝트릴리즈';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.release_id IS '릴리즈ID';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.pid IS '프로젝트ID';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.release_ver IS '릴리즈 버전';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.file_dir IS '파일디렉토리';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.release_dt IS '릴리즈 날짜';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.hashing IS '해싱값';")
cur.execute("COMMENT ON COLUMN dpa_crawler_release_tb.download_dt IS '다운로드 날짜';")

cur.execute("""CREATE TABLE dpa_crawler_project_name_tb (
                   PID             INT   UNIQUE REFERENCES DPA_CRAWLER_PROJECT_TB (pid),
                   PROJECT_NAME    TEXT,
                   DEVELOPER    TEXT,
                   CONSTRAINT project_name_tb_pkey PRIMARY KEY (project_name, developer)
           );""")

cur.execute("COMMENT ON TABLE dpa_crawler_project_name_tb IS '크롤러프로젝트릴리즈';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_name_tb.pid IS '프로젝트ID';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_name_tb.project_name IS '프로젝트명';")
cur.execute("COMMENT ON COLUMN dpa_crawler_project_name_tb.developer IS '개발자명';")

cur.execute("""CREATE TABLE dpa_crawler_commcd_tb (
                   COMM_CD   CHAR(6)    PRIMARY KEY,
                   PRV_CD    CHAR(6)    NOT NULL,
                   PRV_CD_NM    TEXT,
                   USE_YN       TEXT,
                   COMM_DESC    TEXT
           );""")

cur.execute("COMMENT ON TABLE dpa_crawler_commcd_tb IS '크롤러프로젝트릴리즈';")
cur.execute("COMMENT ON COLUMN dpa_crawler_commcd_tb.comm_cd IS '공통코드';")
cur.execute("COMMENT ON COLUMN dpa_crawler_commcd_tb.prv_cd IS '공통상세코드';")
cur.execute("COMMENT ON COLUMN dpa_crawler_commcd_tb.prv_cd_nm IS '상세코드명';")
cur.execute("COMMENT ON COLUMN dpa_crawler_commcd_tb.comm_desc IS '설명';")

conn.commit()