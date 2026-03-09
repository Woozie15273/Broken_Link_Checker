import pytest
import json
from pathlib import Path

from src.crawler import ValidationResult

def pytest_configure(config):
    config.option.asyncio_mode = "auto"

@pytest.fixture(scope='session')
def project_root():
    return Path(__file__).resolve().parent.parent

@pytest.fixture(scope='session', params=['targets.json'])
def targets(request, project_root):
    json_path = project_root / "data" / request.param
    with open(json_path, 'r') as f:
        return json.load(f)
    
@pytest.fixture(scope="session")
def mock_results():
    """Provides a static list of 18 library links for offline testing."""
    return [
        ValidationResult(url='https://bowenlibrary.ca/calendar', text='BOWEN ISLAND', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://www.bpl.bc.ca/events', text='BURNABY', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://www.coqlibrary.ca/programs-events/esl-programs-and-services', text='COQUITLAM', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://www.fvrl.bc.ca/events', text='FRASER VALLEY', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://gibsons.bc.libraries.coop/calendar', text='GIBSONS & DISTRICT', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://lillooet.bc.libraries.coop/calendar', text='LILLOOET AREA ASSOCIATION', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://www.nwpl.ca/events-calendar', text='NEW WESTMINSTER', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://www.nvcl.ca/calendar', text='NORTH VANCOUVER CITY', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://nvdpl.ca/programs-events', text='NORTH VANCOUVER DISTRICT', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://pembertonlibrary.ca/library-events-calendar', text='PEMBERTON & DISTRICT', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://calendar.portmoodylibrary.ca/default/Month', text='PORT MOODY', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://www.yourlibrary.ca/events-calendar', text='RICHMOND', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://sechelt.bc.libraries.coop/calendar', text='SECHELT', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://squamish.bc.libraries.coop/calendar', text='SQUAMISH', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://www.surreylibraries.ca/events', text='SURREY LIBRARIES', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://vpl.bibliocommons.com/events/search/index', text='VANCOUVER', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='https://westvanlibrary.ca/events-programs', text='WEST VANCOUVER MEMORIAL', parent='https://newtobc.ca/library-information/library-programs'),
        ValidationResult(url='http://www.whistlerlibrary.ca/events', text='WHISTLER', parent='https://newtobc.ca/library-information/library-programs')
    ]