-- Station 1: relational model. Money = DECIMAL (never FLOAT).
IF OBJECT_ID('dbo.companies','U') IS NULL
CREATE TABLE dbo.companies (
    company_id INT IDENTITY(1,1) PRIMARY KEY,
    ticker     NVARCHAR(10)  NOT NULL UNIQUE,
    name       NVARCHAR(200) NULL,
    sector     NVARCHAR(60)  NOT NULL,
    industry   NVARCHAR(120) NULL,
    cik        NVARCHAR(10)  NULL
)
GO
IF OBJECT_ID('dbo.prices','U') IS NULL
CREATE TABLE dbo.prices (
    price_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
    company_id  INT  NOT NULL REFERENCES dbo.companies(company_id),
    trade_date  DATE NOT NULL,
    open_price  DECIMAL(18,4) NOT NULL,
    high_price  DECIMAL(18,4) NOT NULL,
    low_price   DECIMAL(18,4) NOT NULL,
    close_price DECIMAL(18,4) NOT NULL,
    adj_close   DECIMAL(18,4) NOT NULL,
    volume      BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uq_prices UNIQUE (company_id, trade_date)
)
GO
IF OBJECT_ID('dbo.fundamentals','U') IS NULL
CREATE TABLE dbo.fundamentals (
    fundamental_id     INT IDENTITY(1,1) PRIMARY KEY,
    company_id         INT NOT NULL REFERENCES dbo.companies(company_id),
    fiscal_year        INT NOT NULL,
    period_end         DATE NULL,
    revenue            DECIMAL(24,2) NULL,
    net_income         DECIMAL(24,2) NULL,
    ebitda             DECIMAL(24,2) NULL,
    total_assets       DECIMAL(24,2) NULL,
    total_liabilities  DECIMAL(24,2) NULL,
    total_debt         DECIMAL(24,2) NULL,
    cash               DECIMAL(24,2) NULL,
    eps                DECIMAL(18,4) NULL,
    shares_outstanding DECIMAL(24,0) NULL,
    CONSTRAINT uq_fund UNIQUE (company_id, fiscal_year)
)
GO
-- Derived data lives apart: a formula bug is fixed by recomputing, raw statements stay untouched.
IF OBJECT_ID('dbo.ratios','U') IS NULL
CREATE TABLE dbo.ratios (
    ratio_id       INT IDENTITY(1,1) PRIMARY KEY,
    company_id     INT NOT NULL REFERENCES dbo.companies(company_id),
    fiscal_year    INT NOT NULL,
    pe_ratio       DECIMAL(18,4) NULL,
    profit_margin  DECIMAL(18,4) NULL,
    roe            DECIMAL(18,4) NULL,
    roa            DECIMAL(18,4) NULL,
    debt_to_equity DECIMAL(18,4) NULL,
    CONSTRAINT uq_ratios UNIQUE (company_id, fiscal_year)
)
GO
-- Audit log written by the FastAPI layer.
IF OBJECT_ID('dbo.audit_log','U') IS NULL
CREATE TABLE dbo.audit_log (
    audit_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    question   NVARCHAR(MAX) NOT NULL,
    tools_used NVARCHAR(500) NULL,
    answer     NVARCHAR(MAX) NULL,
    latency_ms INT NULL,
    status     NVARCHAR(20) NOT NULL DEFAULT 'ok'
)
