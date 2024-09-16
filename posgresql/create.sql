CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE employee (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TYPE organization_type AS ENUM (
    'IE',
    'LLC',
    'JSC'
);

CREATE TABLE organization (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type organization_type,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE organization_responsible (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organization(id) ON DELETE CASCADE,
    user_id UUID REFERENCES employee(id) ON DELETE CASCADE
);

CREATE TYPE tender_status AS ENUM (
    'Created',
    'Published',
    'Closed'
);

CREATE TABLE tender (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    active_version int CHECK (active_version >= 1) DEFAULT 1,
    status tender_status NOT NULL,
    organization_id UUID REFERENCES organization(id) ON DELETE CASCADE,
    creator_username VARCHAR(50) REFERENCES employee(username),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tender_version (
    tender_id UUID NOT NULL REFERENCES tender(id) ON DELETE CASCADE,
    version int CHECK (version >= 1) DEFAULT 1,
    name VARCHAR(100),
    description VARCHAR(500),
    service_type VARCHAR(20) NOT NULL,
    UNIQUE (tender_id, version)
);

CREATE TYPE bid_status AS ENUM (
    'Created',
    'Published',
    'Canceled'
);

CREATE TYPE bid_desision AS ENUM (
    'Approved',
    'Rejected'
);

CREATE TABLE bid (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status bid_status DEFAULT 'Created',
    desision bid_desision,
    active_version int CHECK (active_version >= 1) DEFAULT 1,
    tender_id UUID REFERENCES tender(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organization(id),
    creatorUsername VARCHAR(50) REFERENCES employee(username),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bid_version (
    bid_id UUID NOT NULL REFERENCES bid(id) ON DELETE CASCADE,
    version int CHECK (version >= 1) DEFAULT 1,
    name VARCHAR(100),
    description VARCHAR(500),
    UNIQUE (bid_id, version)
);

CREATE OR REPLACE FUNCTION check_employee_in_organization()
RETURNS TRIGGER AS $$
DECLARE
    employee_count INT;
BEGIN
    SELECT COUNT(*)
    INTO employee_count
    FROM organization_responsible
    WHERE organization_id = NEW.organization_id
      AND user_id = (SELECT id FROM employee WHERE username = NEW.creator_username);

    IF employee_count = 0 THEN
        RAISE EXCEPTION 'Employee % is not a member of the organization %', NEW.creator_username, NEW.organization_id;
    END IF;

    RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER validate_tender_organization
BEFORE INSERT OR UPDATE ON tender
FOR EACH ROW
EXECUTE FUNCTION check_employee_in_organization();

CREATE TRIGGER validate_bid_organization
BEFORE INSERT OR UPDATE ON bid
FOR EACH ROW
EXECUTE FUNCTION check_employee_in_organization();

