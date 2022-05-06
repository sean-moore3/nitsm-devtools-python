import os.path
import pytest
import win32com.client
import win32com.client.selecttlb
import pythoncom
import nitsm.codemoduleapi

_standalone_tsm_context_tlb = win32com.client.selecttlb.FindTlbsWithDescription(
    "NI TestStand Semiconductor Module Standalone Semiconductor Module Context"
)[0]


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


class StandaloneSMC(nitsm.codemoduleapi.SemiconductorModuleContext):
    def __init__(self, tsm_com_obj, file_paths: dict = {}):
        super().__init__(tsm_com_obj)
        self.specifications_files = []
        self.levels_files = []
        self.timing_files = []
        self.pattern_files = []
        self.source_waveform_files = []
        self.capture_waveform_files = []
        self.specifications_files = file_paths.get("specifications", self.specifications_files)
        self.levels_files = file_paths.get("levels", self.levels_files)
        self.timing_files = file_paths.get("timing", self.timing_files)
        self.pattern_files = file_paths.get("pattern", self.pattern_files)
        self.source_waveform_files = file_paths.get("source_waveforms", self.source_waveform_files)
        self.capture_waveform_files = file_paths.get(
            "capture_waveforms", self.capture_waveform_files
        )

    @property
    def nidigital_project_specifications_file_paths(self):
        return self.specifications_files

    @property
    def nidigital_project_levels_file_paths(self):
        return self.levels_files

    @property
    def nidigital_project_timing_file_paths(self):
        return self.timing_files

    @property
    def nidigital_project_pattern_file_paths(self):
        return self.pattern_files

    @property
    def nidigital_project_source_waveform_file_paths(self):
        return self.source_waveform_files

    @property
    def nidigital_project_capture_waveform_file_paths(self):
        return self.capture_waveform_files


@pytest.fixture
def _published_data_reader_factory(request):
    # get absolute path of the pin map file which is assumed to be relative to the test module
    pin_map_path = request.node.get_closest_marker("pin_map").args[0]
    module_directory = os.path.join(os.path.dirname(request.module.__file__), "LoopBack")
    pin_map_path = os.path.join(module_directory, pin_map_path)

    published_data_reader_factory = win32com.client.Dispatch(
        "NationalInstruments.TestStand.SemiconductorModule.Restricted.PublishedDataReaderFactory"
    )
    print()
    print(pin_map_path)
    print()
    return published_data_reader_factory.NewSemiconductorModuleContext(pin_map_path)


@pytest.fixture
def published_data_reader(_published_data_reader_factory):
    return PublishedDataReader(_published_data_reader_factory[1])


data_dir = os.path.join(os.path.dirname(__file__), "LoopBack")
specification1 = os.path.join(os.path.join(data_dir, "Specifications"), "I2C_Electrical.specs")
specification2 = os.path.join(os.path.join(data_dir, "Specifications"), "I2C_Time.specs")
level = os.path.join(os.path.join(data_dir, "Levels"), "I2C_Levels.digilevels")
timing = os.path.join(os.path.join(data_dir, "Timing"), "I2C_Timing.digitiming")
pattern1 = os.path.join(os.path.join(data_dir, "Patterns"), "I2C_Write_Loop.digipat")
pattern2 = os.path.join(os.path.join(data_dir, "Patterns"), "I2C_Read_Loop.digipat")
pattern3 = os.path.join(os.path.join(data_dir, "Patterns"), "I2C_Write.digipat")
pattern4 = os.path.join(os.path.join(data_dir, "Patterns"), "I2C_Read.digipat")
cap_wfm = os.path.join(os.path.join(data_dir, "Waveforms"), "I2C_Capture_Buffer.digicapture")
src_wfm1 = os.path.join(os.path.join(data_dir, "Waveforms"), "I2C_Broadcast.tdms")
src_wfm2 = os.path.join(os.path.join(data_dir, "Waveforms"), "I2C_SiteUnique.tdms")
src_wfm3 = os.path.join(os.path.join(data_dir, "Waveforms"), "I2C_Source_Buffer.tdms")
digital_project_files = {
    "specifications": [specification1, specification2],
    "levels": [level],
    "timing": [timing],
    "pattern": [pattern1, pattern2, pattern3, pattern4],
    "capture_waveforms": [cap_wfm],
    "source_waveforms": [src_wfm1, src_wfm2, src_wfm3],
}


@pytest.fixture
def standalone_tsm(_published_data_reader_factory):
    # tsm_context = nitsm.codemoduleapi.SemiconductorModuleContext(_published_data_reader_factory[0])
    tsm_context = StandaloneSMC(_published_data_reader_factory[0], file_paths=digital_project_files)
    return tsm_context


@pytest.fixture
def tests_pins(request):
    """
    Need to improve this logic for supplying test pins
    using @pytest.mark.parametrize
    """
    _, file_name = os.path.split(request.module.__file__)
    if file_name == "test_dcpower.py":  # overriding the pin_select as it is inside dcpower module
        # for SMU driver i.e. nidcpower Testing
        smu_system_pins = ["SMU_VI_VCC"]
        input_dut_pins = ["SMU_VI_V_In"]
        output_dut_pins = ["SMU_VI_V_Out"]
        all_smu_pins = ["SMU_PG_Logic"]  # pin group name
        pins_selected = [smu_system_pins, input_dut_pins, output_dut_pins, all_smu_pins]
    elif file_name == "test_digital.py":
        # for Digital pattern instrument driver i.e. nidigital Testing
        input_dut_pins = ["DPI_DO_SCL", "DPI_DO_SDA"]
        output_dut_pins = ["DPI_DI_SCL", "DPI_DI_SDA"]
        all_dut_pins = input_dut_pins + output_dut_pins
        dpi_system_pins = ["DPI_PM_VDD", "DPI_PM_VDDIO"]
        pins_selected = [input_dut_pins, output_dut_pins, all_dut_pins]
    elif file_name == "test_scope.py":
        # for scope driver i.e. niscope testing
        input_dut_pins = ["OSC_xA_P_In"]
        output_dut_pins = ["OSC_xA_P_Out"]
        all_dut_pins = input_dut_pins + output_dut_pins
        pins_selected = [input_dut_pins, output_dut_pins, all_dut_pins]
    elif file_name == "test_daqmx.py":
        # for daqmx driver i.e. nidaqmx testing
        pins_selected = [["DAQ_Pins1"], ["DAQ_Pins2"]]
    elif file_name == "test_abstract.py":
        # for daqmx driver i.e. niabstract testing
        pins_selected = [["BUCK_TLOAD_CTRL"], ["eN_Digital"]]
    elif file_name == "test_fgen.py":
        # for function generator driver i.e. nifgen testing
        input_dut_pins = ["FGN_SI_SGL_In"]
        pins_selected = [input_dut_pins]
    elif file_name == "test_switch.py":
        # for function generator driver i.e. niswitch testing
        input_dut_pins = ["Pin1", "Pin2", "Pin3", "Pin4", "Pin5", "Pin6", "Pin7", "Pin8", "Pin9"]
        pins_selected = input_dut_pins
    elif file_name == "test_fpga.py":
        # for function generator driver i.e. nifpga testing
        input_dut_pins = ["RIO_Pins"]
        pins_selected = [input_dut_pins]
    elif file_name == "test_dmm.py":
        # for function generator driver i.e. nifpga testing
        input_dut_pins = ["CH0"]
        pins_selected = [input_dut_pins]
    else:
        pins_selected = ["dummy", "pins", "to_fail"]
    return pins_selected
