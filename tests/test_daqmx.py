import os
import typing

import nidaqmx
import nidaqmx.constants as constant
import nidevtools.daqmx as ni_daqmx
import nitsm
import pytest
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["MonoLithic.pinmap", "Rainbow.pinmap"]
# Change index below to change the pin map to use
pin_file_name = pin_file_names[0]

OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "6368"}}

# Types Definition
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


@pytest.fixture
def tsm_context(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_daqmx.set_task(standalone_tsm)
    yield standalone_tsm
    ni_daqmx.clear_task(standalone_tsm)


@pytest.fixture
def daqmx_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    print(tests_pins)
    daqmx_tsms = []
    sessions = []
    for test_pin_group in tests_pins:
        print(test_pin_group)
        data = ni_daqmx.pins_to_session_sessions_info(tsm_context, test_pin_group)
        daqmx_tsms.append(data)
        sessions += data.sessions
    print(sessions)
    test = (tsm_context, daqmx_tsms)
    yield test


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDaqmx:
    def test_set_task(self, tsm_context):
        print(tsm_context.pin_map_file_path)
        queried_tasks = tsm_context.get_all_nidaqmx_tasks("AnalogInput")
        assert isinstance(queried_tasks, tuple)  # Type verification
        for task in queried_tasks:
            print("\nTest_set/clear_task\n", task)
            assert isinstance(task, nidaqmx.Task)  # Type verification
            assert len(queried_tasks) != 0  # not void
            assert len(queried_tasks) == 2  # Matching quantity

    def test_pin_to_sessions_info(self, daqmx_tsm_s):
        tsm_context = daqmx_tsm_s[0]
        list_daqmx_tsm = daqmx_tsm_s[1]
        print(list_daqmx_tsm)
        for daqmx_tsm in list_daqmx_tsm:
            print("\nTest_pin_to_sessions\n", daqmx_tsm)
            print(daqmx_tsm.sessions)
            assert isinstance(daqmx_tsm, ni_daqmx.MultipleSessions)
            assert isinstance(daqmx_tsm.pin_query_context, ni_daqmx.PinQuery)
            assert isinstance(daqmx_tsm.sessions, typing.List)
            assert len(daqmx_tsm.sessions) == len(tsm_context.site_numbers)

    def test_get_all_instrument_names(self, tsm_context):
        data = ni_daqmx.get_all_instrument_names(tsm_context)
        print("\nTest Instrument Names: \n", data)
        assert type(data) == tuple
        for element in data:
            assert type(element) == tuple
            assert len(element) != 0

    def test_get_all_sessions(self, tsm_context):
        data = ni_daqmx.get_all_sessions(tsm_context)
        print("\nTest Sessions: \n", data)
        assert type(data) == tuple
        assert len(data) != 0
        for element in data:
            assert isinstance(element, nidaqmx.Task)

    def test_properties(self, daqmx_tsm_s):
        list_daqmx_tsm = daqmx_tsm_s[1]
        print("\nTest Start/Stop All\n")
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.start_task()
            daqmx_tsm.read_waveform(samples_per_channel=1)
            daqmx_tsm.stop_task()
        print("\nTest Timing Configuration\n")
        samp_cha = 1000
        samp_rate = 500
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.timing(samp_cha, samp_rate)
            for session in daqmx_tsm.sessions:
                assert samp_rate == session.Task.timing.samp_clk_rate
        # print("\nTest Trigger Configuration\n")
        # source = "APFI0"
        # for daqmx_tsm in list_daqmx_tsm:
        #     daqmx_tsm.reference_analog_edge(source, constant.Slope.FALLING, 0.0, 500)
        #     for session in daqmx_tsm.sessions:
        #         assert source in session.Task.triggers.reference_trigger.analog_edge_src
        # source = "PXI_Trig0"
        # for daqmx_tsm in list_daqmx_tsm:
        #     daqmx_tsm.reference_digital_edge(source, constant.Slope.FALLING, 10)
        #     for session in daqmx_tsm.sessions:
        #         assert source in session.Task.triggers.reference_trigger.dig_edge_src
        print("\nTest Configure Read Channels\n")
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.configure_channels()
        print("\nTest Read\n")
        for daqmx_tsm in list_daqmx_tsm:
            print("\nTest Read Single Channel\n")
            daqmx_tsm.start_task()
            data = daqmx_tsm.read_waveform(samples_per_channel=8)
            print(data)
            assert isinstance(data, list)
            daqmx_tsm.stop_task()
            print("\nTest Read Multiple Channels\n")
            daqmx_tsm.start_task()
            data = daqmx_tsm.read_waveform_multichannel(samples_per_channel=2)
            print(data)
            assert isinstance(data, list)
            daqmx_tsm.stop_task()
        print("\nVerify Properties\n")
        for daqmx_tsm in list_daqmx_tsm:
            data = daqmx_tsm.get_task_properties()
            assert isinstance(data, typing.List)
            for task_property in data:
                assert isinstance(task_property, ni_daqmx.TaskProperties)
                assert task_property.SamplingRate == samp_rate

    def test_baku_power_sequence(self, tsm_context):
        daq_pins1 = ["DAQ_Pins1"]
        daq_pins2 = ["DAQ_Pins2"]
        daq_pins_out = ["TestAnalogO"]
        daq_sessions_1 = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins1)
        daq_sessions_2 = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins2)
        daq_sessions_out = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins_out)
        sessions_all = daq_sessions_1.sessions + daq_sessions_2.sessions
        daq_sessions_all = ni_daqmx.MultipleSessions(
            pin_query_context=daq_sessions_1.pin_query_context, sessions=sessions_all
        )
        daq_sessions_all.stop_task()
        daq_sessions_all.timing()
        daq_sessions_out.timing()
        # for s in daq_sessions_2.sessions:
        #    print(s.Task.triggers.reference_trigger.analog_edge_src)
        # daq_sessions_2.reference_digital_edge("PXI_Trig0", constant.Slope.FALLING, 10)
        output = 2.0  # configure output in NI-MAX
        error = 0.00123  # 16 bits with range 20 for both input and output
        daq_sessions_out.write_data([output, output])
        daq_sessions_all.start_task()
        data = daq_sessions_all.read_waveform_multichannel(50)
        for measure in data[16:18]:
            for value in measure:
                assert output + error > value > output - error
        daq_sessions_out.write_data([0, 0])
        print("\nAll measured values within the expected value of: ", output, "+-", error)
        print("\nDevice has been released: ", output, "+-", error)
        daq_sessions_out.stop_task()
        daq_sessions_all.stop_task()

    def test_baku_dsa_write_read(self, tsm_context):
        daq_pins_in_dsa = ["TestIn"]
        daq_pins_out_dsa = ["TestOut2"]
        daq_sessions_out_dsa = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins_out_dsa)
        daq_sessions_in_dsa = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins_in_dsa)
        daq_sessions_out_dsa.timing(sampling_rate_hz=1250)  # DSA Channel
        daq_sessions_in_dsa.timing(sampling_rate_hz=10000)  # DSA Channel
        output = 2.0  # configure output in NI-MAX
        error = 0.05  # 16 bits with range 20 for both input and output
        daq_sessions_in_dsa.start_task()
        daq_sessions_out_dsa.write_data([output, output])  # TODO missing write
        data2 = daq_sessions_in_dsa.read_waveform_multichannel(1000)
        value = max(data2[0])
        assert output + error > value > output - error
        print(value)
        print("\nAll measured values within the expected value of: ", output, "+-", error)
        print("\nDevice has been released: ", output, "+-", error)
        daq_sessions_out_dsa.stop_task()
        daq_sessions_in_dsa.stop_task()

    def test_baku_dsa_write_read_wo_pinmap(self):
        taski = nidaqmx.Task("DAQ3_AI")
        tasko = nidaqmx.Task("DAQ3_AO")
        ch_in = taski.ai_channels.add_ai_voltage_chan("DAQ3/ai0")
        ch_out = tasko.ao_channels.add_ao_voltage_chan("DAQ3/ao0")
        tasko.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.ALLOW_REGENERATION
        tasko.timing.cfg_samp_clk_timing(rate=1250)
        taski.timing.cfg_samp_clk_timing(rate=10000)
        print("AI_CHA_CONFIG: ", ch_in.ai_term_cfg, ch_in.ai_coupling)
        print("AO_CHA_CONFIG: ", ch_out.ao_term_cfg, ch_out.physical_channel)
        taski.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        tasko.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        taski.start()
        print(tasko.out_stream.regen_mode)
        tasko.write(5)
        print(max(taski.read(1000)))


@nitsm.codemoduleapi.code_module
def open_sessions(tsm_context: SMContext):
    ni_daqmx.set_task(tsm_context)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SMContext):
    ni_daqmx.clear_task(tsm_context)


@nitsm.codemoduleapi.code_module
def pins_to_sessions(
    tsm_context: SMContext,
    pins: typing.List[str],
):
    return ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)


@nitsm.codemoduleapi.code_module
def configure(
    tsm_context: SMContext,
    pins: typing.List[str],
):
    tsm_multi_session: ni_daqmx.MultipleSessions
    tsm_multi_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    # Timing Configuration
    tsm_multi_session.timing(1000, 500)
    # Trigger Configuration
    tsm_multi_session.reference_analog_edge("APFI0")
    tsm_multi_session.reference_digital_edge("PXI_Trig0", constant.Slope.FALLING, 10)
    # Configure Read Channels
    tsm_multi_session.configure_channels()
    # Get Properties
    data = tsm_multi_session.get_task_properties()
    return data


@nitsm.codemoduleapi.code_module
def acquisition_single_ch(
    tsm_context: SMContext,
    pins: typing.List[str],
):
    tsm_multi_session: ni_daqmx.MultipleSessions
    tsm_multi_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    tsm_multi_session.start_task()
    yield tsm_multi_session.read_waveform()
    tsm_multi_session.stop_task()


@nitsm.codemoduleapi.code_module
def acquisition_multi_ch(
    tsm_context: SMContext,
    pins: typing.List[str],
):
    tsm_multi_session: ni_daqmx.MultipleSessions
    tsm_multi_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    tsm_multi_session.start_task()
    yield tsm_multi_session.read_waveform_multichannel()
    tsm_multi_session.stop_task()


@nitsm.codemoduleapi.code_module
def scenario1(tsm_context: SMContext):
    daq_pins1 = ["DAQ_Pins1"]
    daq_pins2 = ["DAQ_Pins2"]
    daq_pins_out = ["TestAnalogO"]
    daq_sessions_1 = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins1)
    daq_sessions_2 = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins2)
    daq_sessions_out = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins_out)
    sessions_all = daq_sessions_1.sessions + daq_sessions_2.sessions
    daq_sessions_all = ni_daqmx.MultipleSessions(
        pin_query_context=daq_sessions_1.pin_query_context, sessions=sessions_all
    )
    daq_sessions_all.stop_task()
    daq_sessions_all.timing()
    daq_sessions_out.timing()
    output = 2.0
    daq_sessions_out.write_data([output, output])
    daq_sessions_all.start_task()
    data = daq_sessions_all.read_waveform_multichannel(50)
    yield data
    daq_sessions_out.write_data([0, 0])
    daq_sessions_out.stop_task()
    daq_sessions_all.stop_task()


@nitsm.codemoduleapi.code_module
def scenario2(tsm_context: SMContext):
    daq_pins_in_dsa = ["TestIn"]
    daq_pins_out_dsa = ["TestOut2"]
    daq_sessions_out_dsa = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins_out_dsa)
    daq_sessions_in_dsa = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins_in_dsa)
    daq_sessions_out_dsa.timing(sampling_rate_hz=1250)  # DSA Channel
    daq_sessions_in_dsa.timing(sampling_rate_hz=10000)  # DSA Channel
    expected = 2.0  # configure expected in NI-MAX
    daq_sessions_in_dsa.start_task()
    daq_sessions_out_dsa.write_data([expected, expected])
    data2 = daq_sessions_in_dsa.read_waveform_multichannel(1000)
    value = max(data2[0])
    yield value
    daq_sessions_out_dsa.stop_task()
    daq_sessions_in_dsa.stop_task()
