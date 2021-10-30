import os.path
import pytest
import win32com.client
import win32com.client.selecttlb
import pythoncom
import nitsm.codemoduleapi

_standalone_tsm_context_tlb = win32com.client.selecttlb.FindTlbsWithDescription(
    "NI TestStand Semiconductor Module Standalone Semiconductor Module Context"
)[0]


@pytest.fixture
def test_pin_s(request):
    """
    Need to improve this logic for supplying test pins
    using @pytest.mark.parametrize
    """
    _, file_name = os.path.split(request.module.__file__)
    print(file_name)
    if file_name == "test_dcpower.py":  # overriding the pin_select as it is inside dcpower module
        # for SMU driver i.e. nidcpower Testing
        smu_system_pins = ["VCC"]
        input_dut_pins = ["A", "B"]
        output_dut_pins = ["C_Y", "Y"]
        all_smu_pins = input_dut_pins + output_dut_pins
        pins_selected = [smu_system_pins, input_dut_pins, output_dut_pins, all_smu_pins]
    elif file_name == "test_digital.py":
        # for Digital pattern instrument driver i.e. nidigital Testing
        test_dut_pins = ["SCL", "SDA"]
        read_dut_pins = ["R_SCL", "R_SDA"]
        all_dut_pins = test_dut_pins + read_dut_pins
        dpi_system_pins = ["VDD", "VDDIO"]
        pins_selected = [test_dut_pins, read_dut_pins, all_dut_pins]
    else:
        pins_selected = []
    print(pins_selected)
    return pins_selected


@pytest.fixture
def _published_data_reader_factory(request):
    # get absolute path of the pin map file which is assumed to be relative to the test module
    pin_map_path = request.node.get_closest_marker("pin_map").args[0]
    module_directory = os.path.join(os.path.dirname(request.module.__file__), "Data")
    pin_map_path = os.path.join(module_directory, pin_map_path)

    published_data_reader_factory = win32com.client.Dispatch(
        "NationalInstruments.TestStand.SemiconductorModule.Restricted.PublishedDataReaderFactory"
    )
    return published_data_reader_factory.NewSemiconductorModuleContext(pin_map_path)


@pytest.fixture
def standalone_tsm_context(_published_data_reader_factory):
    return nitsm.codemoduleapi.SemiconductorModuleContext(_published_data_reader_factory[0])


class PublishedData:
    def __init__(self, published_data_com_obj):
        self._published_data = win32com.client.CastTo(
            published_data_com_obj, "IPublishedData", _standalone_tsm_context_tlb
        )
        self._published_data._oleobj_ = self._published_data._oleobj_.QueryInterface(
            self._published_data.CLSID, pythoncom.IID_IDispatch
        )

    @property
    def boolean_value(self):
        return self._published_data.BooleanValue

    @property
    def double_value(self):
        return self._published_data.DoubleValue

    @property
    def pin(self):
        return self._published_data.Pin

    @property
    def published_data_id(self):
        return self._published_data.PublishedDataId

    @property
    def site_number(self):
        return self._published_data.SiteNumber

    @property
    def string_value(self):
        return self._published_data.StringValue

    @property
    def type(self):
        return self._published_data.Type


class PublishedDataReader:
    def __init__(self, published_data_reader_com_obj):
        self._published_data_reader = win32com.client.CastTo(
            published_data_reader_com_obj, "IPublishedDataReader", _standalone_tsm_context_tlb
        )

    def get_and_clear_published_data(self):
        published_data = self._published_data_reader.GetAndClearPublishedData()
        return [PublishedData(published_data_point) for published_data_point in published_data]


@pytest.fixture
def published_data_reader(_published_data_reader_factory):
    return PublishedDataReader(_published_data_reader_factory[1])
