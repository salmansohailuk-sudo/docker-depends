// Backend is proxied through Nginx at /api — no hardcoded host:port needed.
// Change BACKEND_BASE here if you are running outside Docker (e.g. local dev).
const BACKEND_BASE = '/api';

const bodyStyles = window.getComputedStyle(document.body);
const nameField = document.getElementById('text_name');
const emailField = document.getElementById('text_email');
const phoneField = document.getElementById('text_phone');
const statusField = document.getElementById('text_status');
const statusCodeField = document.getElementById('text_status_code');
const resultsContainer = document.getElementById('results-container');
const tableNameContainer = document.getElementById('table-name');

const allFields = [nameField, emailField, phoneField];

const clearButton = document.getElementById('clear-button');
const defaultValuesButton = document.getElementById('default-values-button');
const submitButton = document.getElementById('submit-form-button');
const testConnectionButton = document.getElementById('test-connection-button');
const viewDataButton = document.getElementById('view-data-button');

const tableTemplate = {
    "tag": "tr",
    "children": [
        {"tag": "td", "html": "${id}"},
        {"tag": "td", "html": "${full_name}"},
        {"tag": "td", "html": "${email}"},
        {"tag": "td", "html": "${phone_number}"},
    ]
};

const tableHeader = "<tr><th>ID</th><th>Name</th><th>Email</th><th>Phone Number</th></tr>";
const tableName = 'USER_ENTITY';

let populateStatusFieldsWithError = (errorType, errors) => {
    let statusFieldRows = 1;
    statusField.value = errorType;
    errors.forEach((eachError) => {
        statusFieldRows++;
        statusField.value += '\r\n - ' + eachError;
    });
    statusField.rows = statusFieldRows;
    statusField.style.color = bodyStyles.getPropertyValue('--error-red');
};

let clearStatusFields = () => {
    statusCodeField.value = 'xxx';
    statusField.value = 'Idle';
    statusField.rows = 1;
    statusField.style.color = 'revert';
};

let destroyResultsTable = () => {
    resultsContainer.textContent = '';
    tableNameContainer.textContent = '';
};

let transformUserResultsToTable = (data) => {
    destroyResultsTable();
    let tableHtml = json2html.render(data, tableTemplate);
    if (tableHtml !== '') {
        tableNameContainer.textContent = tableName;
        resultsContainer.insertAdjacentHTML("afterBegin", tableHeader + tableHtml);
    }
};

let setStatus = (status, responseBody) => {
    statusCodeField.value = status + ' ' + getFriendlyStatus(status);
    if (status === 200 || status === 201) {
        statusField.value = JSON.stringify(responseBody);
        statusField.rows = Math.ceil(statusField.value.length / 36) + 1;
        statusField.style.color = bodyStyles.getPropertyValue('--pastel-green');
    } else {
        populateStatusFieldsWithError(responseBody.type || 'ERROR', responseBody.error || ['Unknown error']);
    }
};

let apiFetch = async (method, path, body) => {
    clearStatusFields();
    try {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(BACKEND_BASE + path, opts);
        const json = await res.json();
        return { status: res.status, body: json };
    } catch (e) {
        statusField.value = 'The backend server is not accessible';
        statusField.style.color = bodyStyles.getPropertyValue('--error-red');
        return null;
    }
};

let testConnection = async () => {
    const r = await apiFetch('GET', '/ping');
    if (r) setStatus(r.status, r.body);
};

let getUserDetails = async () => {
    const r = await apiFetch('GET', '/user');
    if (r) {
        setStatus(r.status, r.body);
        if (r.status === 200) {
            if (r.body.length === 0) {
                statusField.value = 'Received Data : No Results Found';
                statusField.style.color = bodyStyles.getPropertyValue('--pastel-green');
            }
            transformUserResultsToTable(JSON.stringify(r.body));
        }
    }
};

let clearTextFields = () => {
    nameField.value = '';
    emailField.value = '';
    phoneField.value = '';
    clearStatusFields();
    destroyResultsTable();
    allFields.forEach((f) => (f.style.borderBottom = 'revert'));
};

let defaultTextFields = () => {
    nameField.value = 'John Doe';
    emailField.value = 'test@gmail.com';
    phoneField.value = '9876543210';
    clearStatusFields();
    allFields.forEach((f) => (f.style.borderBottom = 'revert'));
};

let isEmpty = (field) => !field.value;

let validFields = () => {
    let anyEmpty = false;
    allFields.forEach((f) => {
        f.style.borderBottom = 'revert';
        if (isEmpty(f)) {
            anyEmpty = true;
            f.style.borderBottom = '1px solid ' + bodyStyles.getPropertyValue('--error-red');
        }
    });
    return !anyEmpty;
};

let submitCreateUserFields = async () => {
    clearStatusFields();
    if (!validFields()) {
        populateStatusFieldsWithError('EMPTY_FIELDS', ['Fields marked in red were left empty']);
        return;
    }
    const r = await apiFetch('POST', '/user', {
        full_name: nameField.value,
        email: emailField.value,
        phone_number: phoneField.value,
    });
    if (r) setStatus(r.status, r.body);
};

clearButton.addEventListener('click', clearTextFields);
submitButton.addEventListener('click', submitCreateUserFields);
defaultValuesButton.addEventListener('click', defaultTextFields);
testConnectionButton.addEventListener('click', testConnection);
viewDataButton.addEventListener('click', getUserDetails);
