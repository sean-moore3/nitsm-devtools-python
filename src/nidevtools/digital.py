"""
This is nidigital wrapper for use with STS test codes
"""
import copy
from datetime import datetime
from enum import Enum
import os
import re
import typing
from nidigital import enums
import nidigital
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
import nitsm.codemoduleapi
import numpy


class LevelTypeToSet(Enum):
    """
    Levels for various band boundaries

    Args:
        typing.enum : voltage level defines the voltage for High or Low and for Input or Output
    """
    VIL = 0
    VIH = 1
    VOL = 2
    VOH = 3
    VTERM = 4
    IOL = 5
    IOH = 6
    VCOM = 7


class Location1DArray(typing.NamedTuple):
    location_1d_array: typing.List[int]


class Location2D(typing.NamedTuple):
    row: int
    col: int


class Location2DArray(typing.NamedTuple):
    location_2d_array: typing.List[Location2D]


class SessionProperties(typing.NamedTuple):
    instrument_name: str
    voh: float
    vol: float
    vih: float
    vil: float
    vterm: float
    measurement_time: float


class HRAMConfiguration:
    finite_samples: bool = True
    cycles_to_acquire: enums.HistoryRAMCyclesToAcquire = enums.HistoryRAMCyclesToAcquire.FAILED
    max_samples_to_acquire_per_site: int = 8191
    buffer_size_per_site: int = 32000
    pretrigger_samples: int = 0
    trigger_type: enums.HistoryRAMTriggerType = enums.HistoryRAMTriggerType.FIRST_FAILURE
    cycle_number: int = 0
    pattern_label: str = ""
    vector_offset: int = 0
    cycle_offset: int = 0


class PXITriggerLine(typing.NamedTuple):
    NONE: str
    PXI_TRIG0: str
    PXI_TRIG1: str
    PXI_TRIG2: str
    PXI_TRIG3: str
    PXI_TRIG4: str
    PXI_TRIG5: str
    PXI_TRIG6: str
    PXI_TRIG7: str


PXI_TRIGGER_LINE = PXITriggerLine(
    "",
    "PXI_Trig0",
    "PXI_Trig1",
    "PXI_Trig2",
    "PXI_Trig3",
    "PXI_Trig4",
    "PXI_Trig5",
    "PXI_Trig6",
    "PXI_Trig7",
)


class SignalId(typing.NamedTuple):
    PATTERN_OPCODE_EVENT0: str
    PATTERN_OPCODE_EVENT1: str
    PATTERN_OPCODE_EVENT2: str
    PATTERN_OPCODE_EVENT3: str


SIGNAL_ID = SignalId(
    "patternOpcodeEvent0",
    "patternOpcodeEvent1",
    "patternOpcodeEvent2",
    "patternOpcodeEvent3",
)


class _NIDigitalSSC:
    """
    _Site specific _Session and _Channel.
    Each object of this class is used to store info for a specified pin under specific Site.
    To store a _Session and _Channel(s) for many _Site(s) you need an array of this class object.
    Prefix cs is used in all methods that operates on a given channels in a session.
    These are for internal use only and can be changed any time.
    External module should not use these methods with prefix 'cs_' directly.
    """

    def __init__(self, session: nidigital.Session, channels: str, pins: str):
        """
        constructor node for storing the session, channels and pins

        Args:
            session (nidigital.Session): mostly shared session depends on pinmap file.
            channels (str): specific channel(s) of that session for this context.
            pins (str): pins (names) mapped to the channels.
        """
        self._session = session
        self._channels = channels
        self._pins = pins
        self._channels_session = session.channels[channels]  # session with specific channel(s)

    def cs_abort(self):
        """
        Stops bursting the pattern.
        """
        self._session.abort()

    def cs_clock_generator_abort(self):
        """
        Stops clock generation on the specified channel(s) or pin(s) and pin group(s).

        Returns:
            none: when successful otherwise exception will be thrown.
        """
        return self._channels_session.clock_generator_abort()

    def cs_clock_generator_generate_clock(self, frequency: float, select_digital: bool = True):
        """
        Configures clock generator frequency and initiates clock generation on specified channel(s)
        or pin(s) and pin group(s).

        Args:
            frequency (float): The frequency of the clock generation, in Hz.
            select_digital (Bool, optional): A Boolean that specifies whether to select the
            digital method for the pins specified prior to starting clock generation.
            Defaults to True.

        Returns:
            none: when successful otherwise exception will be thrown.
        """
        return self._channels_session.clock_generator_generate_clock(frequency, select_digital)

    def cs_modify_time_set_for_clock_generation(
        self, frequency: float, duty_cycle: float, time_set: str
    ):
        """
        Configures the period of a time set, drive format and drive edge placement for the
        specified pins. Use this method to modify time set values after applying a timing
        sheet with the apply_levels_and_timing method, or to create time sets programmatically
        without the use of timing sheets. This method does not modify the timing sheet file or
        the timing sheet contents that will be used in future calls to apply_levels_and_timing;
        it only affects the values of the current timing context.

        Args:
            frequency (float): Is the inverse of Period for this time set, in Hz.
            duty_cycle (float): is the percentage at which the positive or negative edge
            is placed, 0 to 1.
            time_set (str): The specified time set name
        """
        period = 1 / frequency
        self._session.configure_time_set_period(time_set, period)
        self._channels_session.configure_time_set_drive_edges(
            time_set,
            enums.DriveFormat.RL,
            0,
            0,
            period * duty_cycle,
            period * duty_cycle,
        )

    def cs_select_function(self, function: enums.SelectedFunction):
        """
        Specifies whether digital pattern instrument channels are controlled by the
        pattern sequencer or PPMU, disconnected, or off.
        +-----------------------------+------------------------------------------------------------+
        | Defined Values:             |                                                            |
        +=============================+============================================================+
        | SelectedFunction.DIGITAL    | The pin is connected to the driver, comparator, and active
                                        load methods. The PPMU is not sourcing, but can make voltage
                                        measurements. The state of the digital pin driver when you
                                        change the selected_function to Digital is determined by the
                                        most recent call to the write_static method or the last
                                        vector of the most recently executed pattern burst,
                                        whichever happened last. Use the write_static method to
                                        control the state of the digital pin driver through
                                        software. Use the burst_pattern method to control the state
                                        of the digital pin driver through a pattern. Set the
                                        **selectDigitalFunction** parameter of the burst_pattern
                                        method to True to automatically switch the selected_function
                                        of the pins in the pattern burst to
                                        SelectedFunction.DIGITAL.                                  |
        +-----------------------------+------------------------------------------------------------+
        | SelectedFunction.PPMU       | The pin is connected to the PPMU. The driver, comparator,
                                        and active load are off while this method is selected. Call
                                        the ppmu_source method to source a voltage or current. The
                                        ppmu_source method automatically switches the
                                        selected_function to the PPMU state and starts sourcing
                                        from the PPMU. Changing the selected_function to
                                        SelectedFunction.DISCONNECT, SelectedFunction.OFF, or
                                        SelectedFunction.DIGITAL causes the PPMU to stop sourcing.
                                        If you set the selected_function property to PPMU, the PPMU
                                        is initially not sourcing.                                 |
        +-----------------------------+------------------------------------------------------------+
        | SelectedFunction.OFF        | The pin is electrically connected, and the PPMU and digital
                                        pin driver are off while this method is selected.          |
        +-----------------------------+------------------------------------------------------------+
        | SelectedFunction.DISCONNECT | The pin is electrically disconnected from instrument
                                        methods.Selecting this method causes the PPMU to stop
                                        sourcing priorto disconnecting the pin.                    |
        +-----------------------------+------------------------------------------------------------+

        Args:
            function (enums.SelectedFunction): selected state to change.
        """
        self._session.abort()
        self._channels_session.selected_function = function

    def cs_frequency_counter_configure_measurement_time(self, measurement_time: float):
        """
        Specifies the measurement time for the frequency counter.

        Args:
            measurement_time (float): in seconds or datetime.timedelta
        """
        self._channels_session.frequency_counter_measurement_time = measurement_time

    def cs_frequency_counter_measure_frequency(self):
        """
        Measures the frequency on the specified channel(s) over the specified measurement time.
        All channels in the repeated capabilities should have the same measurement time.


        Returns:
            list[float]: frequencies list
        """
        return self._channels_session.frequency_counter_measure_frequency()

    # HRAM #
    def cs_configure_hram_settings(
        self,
        cycles_to_acquire: enums.HistoryRAMCyclesToAcquire = enums.HistoryRAMCyclesToAcquire.FAILED,
        pretrigger_samples: int = 0,
        max_samples_to_acquire_per_site: int = 8191,
        number_of_samples_is_finite: bool = True,
        buffer_size_per_site: int = 32000,
    ):
        """
        Configures which cycles History RAM acquires after the trigger conditions are met. If you
        configure History RAM to only acquire failed cycles, you must set the pretrigger samples
        for History RAM to 0.
        Args:
            cycles_to_acquire (enums.HistoryRAMCyclesToAcquire, optional): see the below table for
            details. Defaults to enums.HistoryRAMCyclesToAcquire.FAILED.
            +----------------------------------+--------------------------------------------------+
            | Defined Values:                  |                                                  |
            +==================================+==================================================+
            | HistoryRAMCyclesToAcquire.FAILED | Only acquires cycles that fail a compare after the
                                                 triggering conditions are met.                   |
            +----------------------------------+--------------------------------------------------+
            | HistoryRAMCyclesToAcquire.ALL    | Acquires all cycles after the triggering
                                                 conditions are met.                              |
            +----------------------------------+--------------------------------------------------+
            pretrigger_samples (int, optional): number of pretrigger samples to acquire. Defaults
                to 0.
            max_samples_to_acquire_per_site (int, optional): maximum number of samples to acquire.
                Defaults to 8191.
            number_of_samples_is_finite (bool, optional): finite or infinite number of samples.
                Defaults to True.
            buffer_size_per_site (int, optional): buffer size per site. Defaults to 32000.
        """
        self._session.history_ram_cycles_to_acquire = cycles_to_acquire
        self._session.history_ram_pretrigger_samples = pretrigger_samples
        self._session.history_ram_max_samples_to_acquire_per_site = max_samples_to_acquire_per_site
        self._session.history_ram_number_of_samples_is_finite = number_of_samples_is_finite
        self._session.history_ram_buffer_size_per_site = buffer_size_per_site

    def cs_configure_hram_trigger(
        self,
        triggers_type: enums.HistoryRAMTriggerType,
        cycle_number: int = 0,
        pattern_label: str = "",
        cycle_offset: int = 0,
        vector_offset: int = 0,
    ):
        """
        Specifies the type of trigger condition on which History RAM starts acquiring pattern
        information.
        Args:
            triggers_type (enums.HistoryRAMTriggerType): see the below table for details.
            +-------------------------------------+------------------------------------------------+
            | Defined Values:                     |                                                |
            +=====================================+================================================+
            | HistoryRAMTriggerType.FIRST_FAILURE | Starts acquiring pattern information in
                                                    History RAM on the first failed cycle in a
                                                    pattern burst.                                 |
            +-------------------------------------+------------------------------------------------+
            | HistoryRAMTriggerType.CYCLE_NUMBER  | Starts acquiring pattern information in History
                                                    RAM starting from a specified cycle number.    |
            +-------------------------------------+------------------------------------------------+
            | HistoryRAMTriggerType.PATTERN_LABEL | Starts acquiring pattern information in History
                                                    RAM starting from a specified pattern label,
                                                    augmented by vector and cycle offsets.         |
            +-------------------------------------+------------------------------------------------+
            cycle_number (int, optional): cycle number at which trigger happens. Defaults to 0.
            pattern_label (str, optional): pattern label in which trigger happens. Defaults to "".
            cycle_offset (int, optional): cycle offset in the pattern. Defaults to 0.
            vector_offset (int, optional): vector offset in the pattern. Defaults to 0.
        """
        if triggers_type == enums.HistoryRAMTriggerType.FIRST_FAILURE:
            self._session.history_ram_trigger_type = triggers_type
        elif triggers_type == enums.HistoryRAMTriggerType.CYCLE_NUMBER:
            self._session.history_ram_trigger_type = triggers_type
            self._session.cycle_number_history_ram_trigger_cycle_number = cycle_number
        elif triggers_type == enums.HistoryRAMTriggerType.PATTERN_LABEL:
            self._session.history_ram_trigger_type = triggers_type
            self._session.pattern_label_history_ram_trigger_label = pattern_label
            self._session.pattern_label_history_ram_trigger_cycle_offset = cycle_offset
            self._session.pattern_label_history_ram_trigger_vector_offset = vector_offset

    def cs_get_hram_settings(self):
        """
        gets the current HRAM settings in a tuple format

        Returns:
            HRAM_settings(tuple): contains HRAM Cycles to acquire,pretrigger samples, max samples to
            acquire per site, is number of samples finite, and buffer size per site
        """
        return (
            self._session.history_ram_cycles_to_acquire,
            self._session.history_ram_pretrigger_samples,
            self._session.history_ram_max_samples_to_acquire_per_site,
            self._session.history_ram_number_of_samples_is_finite,
            self._session.history_ram_buffer_size_per_site,
        )

    def cs_get_hram_trigger_settings(self):
        """
        returns the tuple containing HRAM trigger type,cycle number, label, cycle offset and vector
        offset

        Returns:
            HRAM tuple: HRAM trigger settings
        """
        return (
            self._session.history_ram_trigger_type,
            self._session.cycle_number_history_ram_trigger_cycle_number,
            self._session.pattern_label_history_ram_trigger_label,
            self._session.pattern_label_history_ram_trigger_cycle_offset,
            self._session.pattern_label_history_ram_trigger_vector_offset,
        )

    def cs_get_fail_count(self):
        """
        Returns the comparison fail count for pins in the repeated capabilities.

        Returns:
            failure_count (list of int): Number of failures in an array. If a site is disabled or
            not enabled for burst, the method does not return data for that site. You can also use
            the get_pin_results_pin_information method to obtain a sorted list of returned sites and
            channels.
        """
        return self._channels_session.get_fail_count()

    def cs_wait_until_done(self, timeout: float = 10):
        """
        Waits until the pattern burst has completed or the timeout has expired.

        Args:
            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
            to complete. If this method does not complete within this time interval, this method
            returns an error. Defaults to 10 seconds.
        """
        self._session.wait_until_done(timeout)

    def cs_apply_tdr_offsets(self, per_instrument_offset: typing.List[float]):
        """
        Applies the correction for propagation delay offsets to a digital pattern instrument. Use
        this method to apply TDR offsets that are stored from a past measurement or are measured by
        means other than the tdr method. Also use this method to apply correction for offsets if the
        **applyOffsets** input of the tdr method was set to False at the time of measurement.

        Args:
            per_instrument_offset (typing.List[float]): TDR offsets to apply, in seconds. Specify an
            offset for each pin or channel.
        """
        self._channels_session.apply_tdr_offsets(per_instrument_offset)

    def cs_configure_active_load(self, vcom: float, iol: float, ioh: float):
        """
        Configures Iol, Ioh, and Vcom levels for the active load on the
        selected pins/channels in the session. The DUT sources or sinks current based on the level
        values. To enable active load, set the termination mode to TerminationMode.ACTIVE_LOAD.
        To disable active load, set the termination mode of the instrument to
        TerminationMode.HIGH_Z or TerminationMode.VTERM.

        Args:
            vcom (float): Commutating voltage level at which the active load circuit
            switches between sourcing current and sinking current.

            iol (float): Maximum current that the DUT sinks while outputting a voltage
            below V\ :sub:`COM`.

            ioh (float): Maximum current that the DUT sources while outputting a voltage
            above V\ :sub:`COM`.
        """
        self._channels_session.configure_active_load_levels(iol, ioh, vcom)

    def cs_configure_single_level(self, level_type_to_set: LevelTypeToSet, setting: float):
        """
        LevelTypeToSet
            VIH or VIL - Specifies the voltage that the digital pattern instrument will apply to the
                input of the DUT when the test instrument drives a logic high (1) or low (0).
            VOH or VOL - Specifies the output voltage from the DUT above (or below) which the
                comparator on the digital pattern test instrument interprets a logic high (H) or
                low (L).
            VTERM - Specifies the termination voltage the digital pattern instrument applies during
                non-drive cycles when the termination mode is set to V :sub:`term`. The instrument
                applies the termination voltage through a 50 Ω parallel termination resistance.
            IOL or IOH - Specifies the current that the DUT sources (or sinks) to the active load
                while outputting a voltage above (or below) VCOM.
            VCOM - Specifies the voltage level at which the active load circuit switches between
                sourcing current and sinking current.

        Args:
            level_type_to_set (LevelTypeToSet): VIH or VIL or VOH or VOL or IOL or IOH or VCOM or
                VTERM
            setting (float) : value to set
        """
        if level_type_to_set == LevelTypeToSet.VIL:
            self._channels_session.vil = setting
        elif level_type_to_set == LevelTypeToSet.VIH:
            self._channels_session.vih = setting
        elif level_type_to_set == LevelTypeToSet.VOL:
            self._channels_session.vol = setting
        elif level_type_to_set == LevelTypeToSet.VOH:
            self._channels_session.voh = setting
        elif level_type_to_set == LevelTypeToSet.VTERM:
            self._channels_session.vterm = setting
        elif level_type_to_set == LevelTypeToSet.IOL:
            self._channels_session.active_load_iol = setting
        elif level_type_to_set == LevelTypeToSet.IOH:
            self._channels_session.active_load_ioh = setting
        elif level_type_to_set == LevelTypeToSet.VCOM:
            self._channels_session.vcom = setting
        self._session.commit()

    def cs_configure_termination_mode(self, termination_mode: enums.TerminationMode):
        """
        Specifies the behavior of the pin during non-drive cycles.
        Args:
            termination_mode (enums.TerminationMode) : value defined as per the table below
        +-----------------------------+------------------------------------------------------------+
        | Defined Values:             |                                                            |
        +=============================+============================================================+
        | TerminationMode.ACTIVE_LOAD | Specifies that, for non-drive pin states (L, H, X, V, M, E)
                                        ,the active load is connected and the instrument sources or
                                        sinks a defined amount of current to load the DUT. The
                                        amount of current sourced by the instrument and therefore
                                        sunk by the DUT is specified by IOL. The amount of current
                                        sunk by the instrument and therefore sourced by the DUT is
                                        specified by IOH. The voltage at which the instrument
                                        changes between sourcing and sinking is specified by VCOM. |
        +-----------------------------+------------------------------------------------------------+
        | TerminationMode.VTERM       | Specifies that, for non-drive pin states (L, H, X, V, M, E)
                                        , the pin driver terminates the pin to the configured VTERM
                                        voltage through a 50 Ω impedance. VTERM is adjustable to
                                        allow for the pin to terminate at a set level. This is
                                        useful for instruments that might operate incorrectly if an
                                        instrument pin is unterminated and is allowed to float to
                                        any voltage level within the instrument voltage range. To
                                        address this issue, enable VTERM by configuring the VTERM
                                        pin level to the desired voltage and selecting the VTERM
                                        termination mode. Setting VTERM to 0 V and selecting the
                                        VTERM termination mode has the effect of connecting a 50 Ω
                                        termination to ground, which provides an effective 50 Ω
                                        impedance for the pin. This can be useful for improving
                                        signal integrity of certain DUTs by reducing reflections
                                        while the DUT drives the pin.                              |
        +-----------------------------+------------------------------------------------------------+
        | TerminationMode.HIGH_Z      | Specifies that, for non-drive pin states (L, H, X, V, M, E)
                                        , the pin driver is put in a high-impedance state and the
                                        active load is disabled.                                   |
        +-----------------------------+------------------------------------------------------------+
        """
        self._channels_session.termination_mode = termination_mode

    def cs_configure_time_set_compare_edge_per_pin(
        self,
        time_set: str,
        compare_strobes: typing.List[float],
    ):
        """
        Configures the strobe edge time for the pins in the context. Use this method to modify time
        set values after applying a timing sheet with the apply_levels_and_timing method, or to
        create time sets programmatically without the use of timing sheets. This method does not
        modify the timing sheet file or the timing sheet contents that will be used in future calls
        to apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.
            compare_strobes (typing.List[float]): Time when the comparison happens within a vector
            period.
        """
        channels, _, _ = _channel_list_to_pins(self._channels)
        for channel, compare_strobe in zip(channels, compare_strobes):
            self._channels_session.configure_time_set_compare_edges_strobe(time_set, compare_strobe)

    def cs_configure_time_set_compare_edge(self, time_set: str, compare_strobe: float):
        """
        Configures the strobe edge time for the specified pins. Use this method to modify time set
        values after applying a timing sheet with the apply_levels_and_timing method, or to create
        time sets programmatically without the use of timing sheets. This method does not modify the
        timing sheet file or the timing sheet contents that will be used in future calls to
        apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.
            compare_strobe (float in seconds): Time when the comparison happens within a vector
                period.
        """
        self._channels_session.configure_time_set_compare_edges_strobe(time_set, compare_strobe)
        # End of Source and Capture Waveforms #

        # Static #

    def cs_read_static(self):
        """
        Reads the current state of comparators for pins you specify in the repeated capabilities.
        If there are uncommitted changes to levels or the termination mode, this method commits
        the changes to the pins.

        Returns:
            data (list of enums.PinState): The returned array of pin states read from the channels
            in the repeated capabilities. Data is returned as per the order you specify in the
            repeated capabilities. If a site is disabled, the method does not return data for that
            site. You can also use the get_pin_results_pin_information method to obtain a sorted
            list of returned sites and channels.

                -   PinState.L: The comparators read a logic low pin state.
                -   PinState.H: The comparators read a logic high pin state.
                -   PinState.M: The comparators read a mid-band pin state.
                -   PinState.V: The comparators read a value that is above VOH and below VOL,
                                which can occur when you set VOL higher than VOH.
        """
        return self._channels_session.read_static()

    def cs_write_static(self, state: enums.WriteStaticPinState, auto_select=True):
        """
        Writes a static state to the specified pins. The selected pins remain in the specified
        state until the next pattern burst or call to this method. If there are uncommitted changes
        to levels or the termination mode, this method commits the changes to the pins. This method
        does not change the selected pin method. If you write a static state to a pin that does not
        have the Digital method selected, the new static state is stored by the instrument, and
        affects the state of the pin the next time you change the selected method to Digital.

        Args:
            state (typing.List[typing.List[enums.WriteStaticPinState]]): Parameter that specifies
            one of the following digital states to assign to each pin per site.

                -   WriteStaticPinState.ZERO: Specifies to drive low.
                -   WriteStaticPinState.ONE: Specifies to drive high.
                -   WriteStaticPinState.X: Specifies to not drive.

            auto_select=True, specifies this function to configure the output function as digital
            automatically. auto_select=False, if the pin is explicitly configured as digital already
            with the tsm_object.ssc.select_function(). Without configuring as digital and
            auto_select as false, this function will not work as expected.
        """
        if auto_select:
            self.cs_select_function(enums.SelectedFunction.DIGITAL)
        self._channels_session.write_static(state)

    # Session Properties #
    def cs_get_properties(self):  # checked _
        """
        Returns the session properties i.e. Voh, Vol, Vih, Vil, Vterm,
        frequency_counter_measurement_time in a named tuple format

        Returns:
            session_property: Named tuple of session property
        """
        instrument_name = ""
        match = re.search(r"[A-Za-z]+[1-9]+", str(self._session))
        if match:
            instrument_name = match.group()
        session_property = SessionProperties(
            instrument_name,
            self._channels_session.voh,
            self._channels_session.vol,
            self._channels_session.vih,
            self._channels_session.vil,
            self._channels_session.vterm,
            self._channels_session.frequency_counter_measurement_time,
        )
        return session_property

    # Trigger #
    def cs_clear_start_trigger_signal(self):
        """
        Disables the Start trigger. Pattern bursting starts immediately after you call the init
        method or the burst_pattern method.
        """
        self._session.start_trigger_type = enums.TriggerType.NONE

    def cs_configure_trigger_signal(
        self, source: str, edge: enums.DigitalEdge = enums.DigitalEdge.RISING
    ):
        """
        Specifies the source terminal for the Start trigger. configures the start_trigger_type
        property as Digital Edge.

        Args:
            source (str): You can specify source terminals in one of two ways. If the digital
            pattern instrument is named Dev1 and your terminal is PXI_Trig0, you can specify the
            terminal with the fully qualified terminal name, /Dev1/PXI_Trig0, or with the shortened
            terminal name, PXI_Trig0. The source terminal can also be a terminal from another
            device, in which case the NI-Digital Pattern Driver automatically finds a route (if one
            is available) from that terminal to the input terminal (going through a physical PXI
            backplane trigger line). For example, you can set the source terminal on Dev1 to be
            /Dev2/StartTrigger.

            +-----------------+--------------------+
            | Defined Values: |                    |
            +=================+====================+
            | PXI_Trig0       | PXI trigger line 0 |
            +-----------------+--------------------+
            | PXI_Trig1       | PXI trigger line 1 |
            +-----------------+--------------------+
            | PXI_Trig2       | PXI trigger line 2 |
            +-----------------+--------------------+
            | PXI_Trig3       | PXI trigger line 3 |
            +-----------------+--------------------+
            | PXI_Trig4       | PXI trigger line 4 |
            +-----------------+--------------------+
            | PXI_Trig5       | PXI trigger line 5 |
            +-----------------+--------------------+
            | PXI_Trig6       | PXI trigger line 6 |
            +-----------------+--------------------+
            | PXI_Trig7       | PXI trigger line 7 |
            +-----------------+--------------------+

            edge (enums.DigitalEdge, optional): rising or falling edge. Defaults to
            enums.DigitalEdge.RISING.
        """
        self._session.digital_edge_start_trigger_source = source
        self._session.digital_edge_start_trigger_edge = edge

    def cs_export_opcode_trigger_signal(self, signal_id: str, terminal: str = ""):
        """
        Specifies the destination terminal for exporting the Pattern Opcode Event. Terminals can be
        specified in one of two ways. If the digital pattern instrument is named Dev1 and your
        terminal is PXI_Trig0, you can specify the terminal with the fully qualified terminal name,
        /Dev1/PXI_Trig0, or with the shortened terminal name, PXI_Trig0.

        +-----------------+--------------------+
        | Defined Values: |                    |
        +=================+====================+
        | PXI_Trig0       | PXI trigger line 0 |
        +-----------------+--------------------+
        | PXI_Trig1       | PXI trigger line 1 |
        +-----------------+--------------------+
        | PXI_Trig2       | PXI trigger line 2 |
        +-----------------+--------------------+
        | PXI_Trig3       | PXI trigger line 3 |
        +-----------------+--------------------+
        | PXI_Trig4       | PXI trigger line 4 |
        +-----------------+--------------------+
        | PXI_Trig5       | PXI trigger line 5 |
        +-----------------+--------------------+
        | PXI_Trig6       | PXI trigger line 6 |
        +-----------------+--------------------+
        | PXI_Trig7       | PXI trigger line 7 |
        +-----------------+--------------------+
        Args:
                signal_id (str): id of the signal that is used for indexing events.
                terminal (str, optional): pxi trigger line name. Defaults to "".
        """
        self._session.pattern_opcode_events[
            signal_id
        ].exported_pattern_opcode_event_output_terminal = terminal

    def cs_ppmu_source(self):
        """
        Starts sourcing voltage or current from the PPMU. This method automatically selects the PPMU
        method. Changes to PPMU source settings do not take effect until you call this method. If
        you modify source settings after you call this method, you must call this method again for
        changes in the configuration to take effect.
        """
        self._channels_session.ppmu_source()

    def cs_ppmu_source_current(self, current_level: float, current_level_range: float = 0):
        """
        Configures output function as current and selects the PPMU method and applies current level
        and range passed as parameters. Starts sourcing current from the PPMU.

        Args:
            current_level (float): current in amps to source on the pins
            current_level_range (float, optional): current range in amps to apply. Defaults to 0.
        """
        if current_level_range == 0:
            current_level_range = abs(current_level)
            if current_level_range > 32e-3:
                current_level_range = 32e-3
            elif current_level_range < 2e-6:
                current_level_range = 2e-6
        self._channels_session.ppmu_output_function = enums.PPMUOutputFunction.CURRENT
        self._channels_session.ppmu_current_level_range = current_level_range
        self._channels_session.ppmu_current_level = current_level
        self.cs_ppmu_source()

    def cs_ppmu_source_voltage(self, voltage_level: float, current_limit_range: float):
        """
        Configures output function as voltage and Current limit is not configured here
        The PXIe-6570 and PXIe-6571 do not support current limits in PPMU voltage mode:
        http://zone.ni.com/reference/en-XX/help/375145e/nidigitalpropref/pnidigital_ppmucurrentlimit/

        Args:
            voltage_level (float): voltage in volts to source on the pins
            current_limit_range (float): current limit range in amps to use.
        """
        current_limit_range = abs(current_limit_range)
        self._channels_session.ppmu_output_function = enums.PPMUOutputFunction.VOLTAGE
        self._channels_session.ppmu_current_limit_range = current_limit_range
        self._channels_session.ppmu_voltage_level = voltage_level
        self.cs_ppmu_source()

    def ps_burst_pattern_pass_fail(
        self, start_label: str, select_digital_function: bool = True, timeout: float = 10
    ):
        """
        Uses the start_label you specify to burst the pattern on the sites you specify. Waits for
        the burst to complete, and returns comparison results for each site. Digital pins retain
        their state at the end of a pattern burst until the first vector of the pattern burst, a
        call to write_static, or a call to apply_levels_and_timing.

        Args:
            start_label (str): Pattern name or exported pattern label from which to start bursting
                the pattern.
            select_digital_function (bool, optional): A Boolean that specifies whether to select the
                digital method for the pins in the pattern prior to bursting. Defaults to True.
            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
                to complete. If this method does not complete within this time interval, this method
                returns an error.Defaults to 10.

        Returns:
            List of pass_fail ({ int: bool, int: bool, ... }): Dictionary where each key is a site
            number and value is pass/fail.
        """
        return list(
            self._session.sites[self._pins]
            .burst_pattern(start_label, select_digital_function, True, timeout)
            .values()
        )

    def ps_burst_pattern(
        self,
        start_label: str,
        select_digital_function: bool = True,
        timeout: float = 10,
        wait_until_done: bool = True,
    ):
        """
        Uses the start_label you specify to burst the pattern on the sites you specify. Waits for
        the burst to complete if wait_until_done is True with a default timeout of 10 seconds.
        Digital pins retain their state at the end of a pattern burst until the first vector of the
        pattern burst, a call to write_static, or a call to apply_levels_and_timing.

        Args:
            start_label (str): Pattern name or exported pattern label from which to start bursting
                the pattern.
            select_digital_function (bool, optional): A Boolean that specifies whether to select the
                digital method for the pins in the pattern prior to bursting. Defaults to True.
            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
                to complete. If this method does not complete within this time interval, this method
                returns an error.Defaults to 10.
            wait_until_done (bool, optional): A Boolean that indicates whether to wait until the
                bursting is complete. Defaults to True.
        """
        self._session.sites[self._pins].burst_pattern(
            start_label, select_digital_function, wait_until_done, timeout
        )

    def ps_get_site_pass_fail(self):
        """
        Returns value as list of pass/fail for each pin in the current context

        Returns:
            pass_fail (List[Bool]): list of pass or fail for each pin
        """
        return list(self._session.sites[self._pins].get_site_pass_fail().values())


class _NIDigitalTSM:
    """
    class to store session site channels

    Returns:
        ssc_object: class to store session site object
    """

    # SSC Digital array or list #
    def __init__(self, sessions_sites_channels: typing.Iterable[_NIDigitalSSC]):
        """ "
        constructor method for digital sessions class object
        """
        self._sscs = sessions_sites_channels

    @property
    def sessions_sites_channels(self):
        """
        returns the list of sessions in the current context

        Returns:
            sessions : digital sessions of all instrument in the context
        """
        return self._sscs

    # Clock Generation #
    def clock_generator_abort(self):
        """
        Stops clock generation on all the channel(s) or pin(s) and pin group(s).

        Returns:
            none: when successful otherwise exception will be thrown.
        """
        for ssc in self._sscs:
            ssc.cs_clock_generator_abort()

    def clock_generator_generate_clock(
        self, frequency: float, select_digital_function: bool = True
    ):
        """
        Configures clock generator frequency and initiates clock generation on all the channel(s) or
        pin(s) and pin group(s).

        Args:
            frequency (float): The frequency of the clock generation, in Hz.
            select_digital_function (bool, optional): A Boolean that specifies whether to select the
                digital method for the pins specified prior to starting clock generation.
                Defaults to True.

        Returns:
            none: when successful otherwise exception will be thrown.
        """
        for ssc in self._sscs:
            ssc.cs_clock_generator_generate_clock(frequency, select_digital_function)

    def modify_time_set_for_clock_generation(
        self, frequency: float, duty_cycle: float, time_set: str
    ):
        """
        Configures the period of a time set, drive format and drive edge placement for all the
        specified pins. Use this method to modify time set values after applying a timing sheet with
        the apply_levels_and_timing method, or to create time sets programmatically without the use
        of timing sheets. This method does not modify the timing sheet file or the timing sheet
        contents that will be used in future calls to apply_levels_and_timing; it only affects the
        values of the current timing context.

        Args:
            frequency (float): Is the inverse of Period for this time set, in Hz.
            duty_cycle (float): Is the percentage at which the positive or negative edge is placed,
                0 to 1.
            time_set (str): The specified time set name
        """
        for ssc in self._sscs:
            ssc.cs_modify_time_set_for_clock_generation(frequency, duty_cycle, time_set)

    # End of Clock Generation #

    # Configuration #
    def select_function(self, function: enums.SelectedFunction):
        """
        Specifies whether digital pattern instrument channels are controlled by the
        pattern sequencer or PPMU, disconnected, or off.
        +-----------------------------+------------------------------------------------------------+
        | Defined Values:             |                                                            |
        +=============================+============================================================+
        | SelectedFunction.DIGITAL    | The pin is connected to the driver, comparator, and active
                                        load methods. The PPMU is not sourcing, but can make voltage
                                        measurements. The state of the digital pin driver when you
                                        change the selected_function to Digital is determined by the
                                        most recent call to the write_static method or the last
                                        vector of the most recently executed pattern burst,
                                        whichever happened last. Use the write_static method to
                                        control the state of the digital pin driver through
                                        software. Use the burst_pattern method to control the state
                                        of the digital pin driver through a pattern. Set the
                                        **selectDigitalFunction** parameter of the burst_pattern
                                        method to True to automatically switch the selected_function
                                        of the pins in the pattern burst to
                                        SelectedFunction.DIGITAL.                                  |
        +-----------------------------+------------------------------------------------------------+
        | SelectedFunction.PPMU       | The pin is connected to the PPMU. The driver, comparator,
                                        and active load are off while this method is selected. Call
                                        the ppmu_source method to source a voltage or current. The
                                        ppmu_source method automatically switches the
                                        selected_function to the PPMU state and starts sourcing
                                        from the PPMU. Changing the selected_function to
                                        SelectedFunction.DISCONNECT, SelectedFunction.OFF, or
                                        SelectedFunction.DIGITAL causes the PPMU to stop sourcing.
                                        If you set the selected_function property to PPMU, the PPMU
                                        is initially not sourcing.                                 |
        +-----------------------------+------------------------------------------------------------+
        | SelectedFunction.OFF        | The pin is electrically connected, and the PPMU and digital
                                        pin driver are off while this method is selected.          |
        +-----------------------------+------------------------------------------------------------+
        | SelectedFunction.DISCONNECT | The pin is electrically disconnected from instrument
                                        methods. Selecting this method causes the PPMU to stop
                                        sourcing prior to disconnecting the pin.                   |
        +-----------------------------+------------------------------------------------------------+

        Args:
            function (enums.SelectedFunction): selected state to change.
        """
        for ssc in self._sscs:
            ssc.cs_select_function(function)

    # End of Configuration #

    # Frequency Measurement #
    def frequency_counter_configure_measurement_time(self, measurement_time: float):
        """
        Specifies the measurement time for the frequency counter.

        Args:
            measurement_time (float): in seconds or datetime.timedelta
        """
        for ssc in self._sscs:
            ssc.cs_frequency_counter_configure_measurement_time(measurement_time)

    def frequency_counter_measure_frequency(self):
        """
        Measures the frequency on all the channel(s) over the specified measurement time.
        All channels in the repeated capabilities should have the same measurement time.

        Returns:
            list [ list[float]]: frequencies list
        """
        per_instrument_frequencies: typing.List[typing.List[float]] = []
        for ssc in self._sscs:
            per_instrument_frequencies.append(ssc.cs_frequency_counter_measure_frequency())
        return per_instrument_frequencies

    # End of Frequency Measurement #

    # HRAM #
    def configure_hram_settings(
        self,
        cycles_to_acquire: enums.HistoryRAMCyclesToAcquire = enums.HistoryRAMCyclesToAcquire.FAILED,
        pretrigger_samples: int = 0,
        max_samples_to_acquire_per_site: int = 8191,
        number_of_samples_is_finite: bool = True,
        buffer_size_per_site: int = 32000,
    ):
        """
        Configures which cycles History RAM acquires after the trigger conditions are met. If you
        configure History RAM to only acquire failed cycles, you must set the pretrigger samples for
        History RAM to 0.
        Args:
            cycles_to_acquire (enums.HistoryRAMCyclesToAcquire, optional): see the below table for
            details. Defaults to enums.HistoryRAMCyclesToAcquire.FAILED.
            +----------------------------------+--------------------------------------------------+
            | Defined Values:                  |                                                  |
            +==================================+==================================================+
            | HistoryRAMCyclesToAcquire.FAILED | Only acquires cycles that fail a compare after
                                                 the triggering conditions are met.               |
            +----------------------------------+--------------------------------------------------+
            | HistoryRAMCyclesToAcquire.ALL    | Acquires all cycles after the triggering
                                                 conditions are met.                              |
            +----------------------------------+--------------------------------------------------+
            pretrigger_samples (int, optional): number of pretrigger samples to acquire. Defaults to
                0.
            max_samples_to_acquire_per_site (int, optional): maximum number of samples to acquire.
                Defaults to 8191.
            number_of_samples_is_finite (bool, optional): finite or infinite number of samples.
                Defaults to True.
            buffer_size_per_site (int, optional): buffer size per site. Defaults to 32000.
        """
        for ssc in self._sscs:
            ssc.cs_configure_hram_settings(
                cycles_to_acquire,
                pretrigger_samples,
                max_samples_to_acquire_per_site,
                number_of_samples_is_finite,
                buffer_size_per_site,
            )

    def configure_hram_trigger(
        self,
        triggers_type: enums.HistoryRAMTriggerType,
        cycle_number: int = 0,
        pattern_label: str = "",
        cycle_offset: int = 0,
        vector_offset: int = 0,
    ):
        """
        Specifies the type of trigger condition on which History RAM starts acquiring pattern
        information.
        Args:
            triggers_type (enums.HistoryRAMTriggerType): see the below table for details.
        +-------------------------------------+--------------------------------------------------+
        | Defined Values:                     |                                                  |
        +=====================================+==================================================+
        | HistoryRAMTriggerType.FIRST_FAILURE | Starts acquiring pattern information in History
                                                RAM on the first failed cycle in a pattern burst.|
        +-------------------------------------+--------------------------------------------------+
        | HistoryRAMTriggerType.CYCLE_NUMBER  | Starts acquiring pattern information in History RAM
                                                starting from a specified cycle number.          |
        +-------------------------------------+--------------------------------------------------+
        | HistoryRAMTriggerType.PATTERN_LABEL | Starts acquiring pattern information in History RAM
                                                starting from a specified pattern label, augmented
                                                by vector and cycle offsets.                      |
        +-------------------------------------+---------------------------------------------------+
            cycle_number (int, optional): cycle number at which trigger happens. Defaults to 0.
            pattern_label (str, optional): pattern label in which trigger happens. Defaults to "".
            cycle_offset (int, optional): cycle offset in the pattern. Defaults to 0.
            vector_offset (int, optional): vector offset in the pattern. Defaults to 0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_hram_trigger(
                triggers_type, cycle_number, pattern_label, cycle_offset, vector_offset
            )

    def configure_hram(self, hram_configuration: HRAMConfiguration = HRAMConfiguration()):
        """
        Configures the History RAM trigger and acqusition settings

        Args:
            hram_configuration (HRAMConfiguration, optional): All HRAM settings in a single object.
            Defaults to HRAMConfiguration().
        """
        number_of_samples_is_finite = hram_configuration.finite_samples
        cycles_to_acquire = hram_configuration.cycles_to_acquire
        pretrigger_samples = hram_configuration.pretrigger_samples
        buffer_size_per_site = hram_configuration.buffer_size_per_site
        max_samples_to_acquire_per_site = hram_configuration.max_samples_to_acquire_per_site
        triggers_type = hram_configuration.trigger_type
        cycle_number = hram_configuration.cycle_number
        pattern_label = hram_configuration.pattern_label
        cycle_offset = hram_configuration.cycle_offset
        vector_offset = hram_configuration.vector_offset
        self.configure_hram_settings(
            cycles_to_acquire,
            pretrigger_samples,
            max_samples_to_acquire_per_site,
            number_of_samples_is_finite,
            buffer_size_per_site,
        )
        self.configure_hram_trigger(
            triggers_type, cycle_number, pattern_label, cycle_offset, vector_offset
        )

    def get_hram_settings(self):
        """
        gets the current HRAM settings in a tuple of lists format

        Returns:
            HRAM_settings(tuple of lists): contains HRAM Cycles to acquire,pretrigger samples, max
            samples to acquire per site, is number of samples finite, and buffer size per site
        """
        per_instrument_cycles_to_acquire: typing.List[enums.HistoryRAMCyclesToAcquire] = []
        per_instrument_pretrigger_samples: typing.List[int] = []
        per_instrument_max_samples_to_acquire_per_site: typing.List[int] = []
        per_instrument_number_of_samples_is_finite: typing.List[bool] = []
        per_instrument_buffer_size_per_site: typing.List[int] = []
        for ssc in self._sscs:
            (
                cycles,
                pretrigger_samples,
                max_samples,
                is_finite,
                buffer_size,
            ) = ssc.cs_get_hram_settings()
            per_instrument_cycles_to_acquire.append(cycles)
            per_instrument_pretrigger_samples.append(pretrigger_samples)
            per_instrument_max_samples_to_acquire_per_site.append(max_samples)
            per_instrument_number_of_samples_is_finite.append(is_finite)
            per_instrument_buffer_size_per_site.append(buffer_size)
        return (
            per_instrument_cycles_to_acquire,
            per_instrument_pretrigger_samples,
            per_instrument_max_samples_to_acquire_per_site,
            per_instrument_number_of_samples_is_finite,
            per_instrument_buffer_size_per_site,
        )

    def get_hram_trigger_settings(self):
        """
        Returns the tuple containing HRAM trigger type,cycle number, label, cycle offset and vector
        offset

        Returns:
            HRAM_trigger_settings (tuple of lists): HRAM trigger settings
        """
        per_instrument_triggers_type: typing.List[enums.HistoryRAMTriggerType] = []
        per_instrument_cycle_number: typing.List[int] = []
        per_instrument_pattern_label: typing.List[str] = []
        per_instrument_cycle_offset: typing.List[int] = []
        per_instrument_vector_offset: typing.List[int] = []
        for ssc in self._sscs:
            (
                trigger_type,
                cycle_number,
                label,
                cycle_offset,
                vector_offset,
            ) = ssc.cs_get_hram_trigger_settings()
            per_instrument_triggers_type.append(trigger_type)
            per_instrument_cycle_number.append(cycle_number)
            per_instrument_pattern_label.append(label)
            per_instrument_cycle_offset.append(cycle_offset)
            per_instrument_vector_offset.append(vector_offset)
        return (
            per_instrument_triggers_type,
            per_instrument_cycle_number,
            per_instrument_pattern_label,
            per_instrument_cycle_offset,
            per_instrument_vector_offset,
        )

    def stream_hram_results(self):
        """
        Returns the pattern information acquired for the specified cycles.If the pattern is using
        the edge multiplier feature, cycle numbers represent tester cycles, each of which may
        consist of multiple DUT cycles. When using pins with mixed edge multipliers, pins may return
        PinState.PIN_STATE_NOT_ACQUIRED for DUT cycles where those pins do not have edges defined.
        Site number on which to retrieve pattern information must be specified via sites repeated
        capability.The method returns an error if more than one site is specified. Pins for which to
        retrieve pattern information must be specified via pins repeated capability.If pins are not
        specified, pin list from the pattern containing the start label is used. Call
        get_pattern_pin_names with the start label to retrieve the pins associated with the pattern
        burst:

        Note:
        Before bursting a pattern, you must configure the History RAM trigger and specify which
        cycles to acquire.

        history_ram_trigger_type should be used to specify the trigger condition on which History
        RAM starts acquiring pattern information.

        If History RAM trigger is configured as HistoryRAMTriggerType.CYCLE_NUMBER,
        cycle_number_history_ram_trigger_cycle_number should be used to specify the cycle number on
        which History RAM starts acquiring pattern information.

        If History RAM trigger is configured as HistoryRAMTriggerType.PATTERN_LABEL,
        pattern_label_history_ram_trigger_label should be used to specify the pattern label from
        which to start acquiring pattern information.
        pattern_label_history_ram_trigger_vector_offset should be used to specify the number of
        vectors following the specified pattern label from which to start acquiring pattern
        information.
        pattern_label_history_ram_trigger_cycle_offset should be used to specify the number of
        cycles following the specified pattern label and vector offset from which to start acquiring
        pattern information.

        For all History RAM trigger conditions, history_ram_pretrigger_samples should be used to
        specify the number of samples to acquire before the trigger conditions are met. If you
        configure History RAM to only
        acquire failed cycles, you must set history_ram_pretrigger_samples to 0.

        history_ram_cycles_to_acquire should be used to specify which cycles History RAM acquires
        after the trigger conditions are met.

        Returns:
            per_site_cycle_information (list of HistoryRAMCycleInformation): Returns a list of
            class instances with the following information about each pattern cycle:
                -  **pattern_name** (str)  Name of the pattern for the acquired cycle.
                -  **time_set_name** (str) Time set for the acquired cycle.
                -  **vector_number** (int) Vector number within the pattern for the acquired cycle.
                    Vector numbers start
                   at 0 from the beginning of the pattern.
                -  **cycle_number** (int) Cycle number acquired by this History RAM sample. Cycle
                    numbers start at 0
                   from the beginning of the pattern burst.
                -  **scan_cycle_number** (int) Scan cycle number acquired by this History RAM
                    sample. Scan cycle numbers. start at 0 from the first cycle of the scan vector.
                    Scan cycle numbers are -1 for cycles that do not have a scan opcode.
                -  **expected_pin_states** (list of lists of enums.PinState) Pin states as expected
                    by the loaded pattern in the order specified in the pin list. Pins without
                    defined edges in the specified DUT cycle will have a value of
                    PinState.PIN_STATE_NOT_ACQUIRED. Length of the outer list will be equal to the
                    value of edge multiplier for the given vector. Length of the inner list will be
                    equal to the number of pins requested.
                -  **actual_pin_states** (list of lists of enums.PinState) Pin states acquired by
                    History RAM in the order specified in the pin list. Pins without defined edges
                    in the specified DUT cycle will have a value of PinState.PIN_STATE_NOT_ACQUIRED.
                   Length of the outer list will be equal to the value of edge multiplier for the
                   given vector. Length of the inner list will be equal to the number of pins
                   requested.
                -  **per_pin_pass_fail** (list of lists of bool) Pass fail information for pins in
                    the order specified in the pin list. Pins without defined edges in the specified
                    DUT cycle will have a value of pass (True). Length of the outer list will be
                    equal to the value of edge multiplier for the given vector. Length of the inner
                    list will be equal to the number of pins requested.
                number_of_samples (int): total number of samples in the record
        """
        per_instrument_per_site_array: typing.List[_NIDigitalSSC] = []
        for ssc in self._sscs:
            channel_list_array, site_list_array, _ = _arrange_channels_per_site(
                ssc._channels, ssc._pins
            )
            for channel, site in zip(channel_list_array, site_list_array):
                per_instrument_per_site_array.append(_NIDigitalSSC(ssc._session, channel, site))
        per_instrument_per_site_cycle_information: typing.List[
            typing.List[HistoryRAMCycleInformation]
        ] = []
        number_of_samples = 0
        for ssc in per_instrument_per_site_array:
            cycle_information: typing.List[HistoryRAMCycleInformation] = []
            read_position = 0
            sum_of_samples_to_read = 0
            stop = False
            while not stop:
                done = ssc._session.is_done()
                _, pins, sites = _channel_list_to_pins(ssc._channels)
                sample_count = ssc._session.sites[ssc._pins].get_history_ram_sample_count()
                samples_to_read = sample_count - read_position
                cycle_information += (
                    ssc._session.sites[sites]
                    .pins[pins]
                    .fetch_history_ram_cycle_information(read_position, samples_to_read)
                )
                read_position = sample_count
                sum_of_samples_to_read += samples_to_read
                if not samples_to_read and done:
                    stop = True
            per_instrument_per_site_cycle_information.append(cycle_information)
            number_of_samples = max(number_of_samples, sum_of_samples_to_read)
        return per_instrument_per_site_cycle_information, number_of_samples

    # End of HRAM #

    # Pattern Actions #
    def abort(self):
        """
        Stops bursting the pattern.
        """
        for ssc in self._sscs:
            ssc.cs_abort()

    def burst_pattern_pass_fail(self, start_label: str, digital: bool = True, timeout: float = 10):
        """
        Uses the start_label you specify to burst the pattern on the sites you specify. Waits for
        the burst to complete, and returns comparison results for each site.Digital pins retain
        their state at the end of a pattern burst until the first vector of the pattern burst, a
        call to write_static, or a call to apply_levels_and_timing.

        Args:
            start_label (str): Pattern name or exported pattern label from which to start bursting
                the pattern.
            digital (bool, optional): A Boolean that specifies whether to select the digital method
                for the pins in the pattern prior to bursting. Defaults to True.
            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
                to complete. If this method does not complete within this time interval, this method
                returns an error.Defaults to 10.

        Returns:
            List of Lists of pass_fail ({ int: bool, int: bool, ... }): Dictionary where each key is
            a site number and value is pass/fail.
        """
        return [s.ps_burst_pattern_pass_fail(start_label, digital, timeout) for s in self._sscs]

    def burst_pattern(
        self,
        start_label: str,
        select_digital_function: bool = True,
        timeout: float = 10,
        wait_until_done: bool = True,
    ):
        """
        Uses the start_label you specify to burst the pattern. Waits for the burst to complete if
        wait_until_done is True with a default timeout of 10 seconds. Digital pins retain their
        state at the end of a pattern burst until the first vector of the pattern burst, a call to
        write_static, or a call to apply_levels_and_timing.

        Args:
            start_label (str): Pattern name or exported pattern label from which to start bursting
                the pattern.
            select_digital_function (bool, optional): A Boolean that specifies whether to select the
                digital method for the pins in the pattern prior to bursting. Defaults to True.
            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
                to complete. If this method does not complete within this time interval, this method
                returns an error.Defaults to 10.
            wait_until_done (bool, optional): A Boolean that indicates whether to wait until the
                bursting is complete. Defaults to True.
        """
        for ssc in self._sscs:
            ssc.ps_burst_pattern(start_label, select_digital_function, timeout, wait_until_done)

    def get_fail_count(self):
        """
        Returns the comparison fail count for pins in the repeated capabilities.

        Returns:
            failure_count (list of lists of int): Number of failures per instrument. If a site is
            disabled or not enabled for burst, the method does not return data for that site. You
            can also use the get_pin_results_pin_information method to obtain a sorted list of
            returned sites and channels.
        """
        per_instrument_failure_counts = [ssc.cs_get_fail_count() for ssc in self._sscs]
        return per_instrument_failure_counts

    def get_site_pass_fail(self):
        """
        Returns value as list of pass/fail for each pin in the current context

        Returns:
            pass_fail (List[Bool]): list of pass or fail for each pin
        """
        per_instrument_pass: typing.List[typing.List[bool]] = []
        for ssc in self._sscs:
            per_instrument_pass.append(ssc.ps_get_site_pass_fail())
        return per_instrument_pass

    def wait_until_done(self, timeout: float = 10):
        """
        Waits until the pattern burst has completed or the timeout has expired.

        Args:
            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
            to complete. If this method does not complete within this time interval, this method
            returns an error. Defaults to 10 seconds.
        """
        for ssc in self._sscs:
            ssc.cs_wait_until_done(timeout)

    # End of Pattern Actions #

    # Pin Levels and Timing #
    def apply_levels_and_timing(self, levels_sheet: str, timing_sheet: str):
        """
        Applies digital levels and timing values defined in previously loaded levels and timing
        sheets. When applying a levels sheet, only the levels specified in the sheet are affected.
        Any levels not specified in the sheet remain unchanged. When applying a timing sheet, all
        existing time sets are deleted before the new time sets are loaded.

        Args:
            levels_sheet (str): Name of the levels sheet to apply. Use the name of the sheet or pass
            the absolute file path you use in the load_specifications_levels_and_timing method. The
            name of the levels sheet is the file name without the directory and file extension.

            timing_sheet (str): Name of the timing sheet to apply. Use the name of the sheet or pass
            the absolute file path that you use in the load_specifications_levels_and_timing method.
            The name of the timing sheet is the file name without the directory and file extension.
        """
        for ssc in self._sscs:
            ssc._session.sites[ssc._pins].apply_levels_and_timing(levels_sheet, timing_sheet)

    def apply_tdr_offsets(self, per_instrument_offsets: typing.List[typing.List[float]]):
        """
        Applies the correction for propagation delay offsets to a digital pattern instrument. Use
        this method to apply TDR offsets that are stored from a past measurement or are measured by
        means other than the tdr method. Also use this method to apply correction for offsets if the
        **applyOffsets** input of the tdr method was set to False at the time of measurement.

        Args:
            per_instrument_offsets (typing.List[typing.List[float]]): TDR offsets to apply, in
            seconds. Specify an offset for each pin or channel.
        """
        for ssc, per_instrument_offset in zip(self._sscs, per_instrument_offsets):
            ssc.cs_apply_tdr_offsets(per_instrument_offset)

    def configure_active_load(self, vcom: float, iol: float, ioh: float):
        """
        Configures I\ :sub:`OL`, I\ :sub:`OH`, and V\ :sub:`COM` levels for the active load
        on the pins in the context. The DUT sources or sinks current based on the level values.
        To enable active load, set the termination mode to TerminationMode.ACTIVE_LOAD.
        To disable active load, set the termination mode of the instrument to
        TerminationMode.HIGH_Z or TerminationMode.VTERM.

        Args:
            vcom (float): Commutating voltage level at which the active load circuit
            switches between sourcing current and sinking current.

            iol (float): Maximum current that the DUT sinks while outputting a voltage
            below V\ :sub:`COM`.

            ioh (float): Maximum current that the DUT sources while outputting a voltage
            above V\ :sub:`COM`.
        """
        for ssc in self._sscs:
            ssc.cs_configure_active_load(vcom, iol, ioh)

    def configure_single_level_per_site(
        self,
        level_type_to_set: LevelTypeToSet,
        per_site_value: typing.List[typing.List[float]],
    ):
        """
        LevelTypeToSet
            VIH or VIL - Specifies the voltage that the digital pattern instrument will apply to the
                input of the DUT when the test instrument drives a logic high (1) or low (0).
            VOH or VOL - Specifies the output voltage from the DUT above (or below) which the
                comparator on the digital pattern test instrument interprets a logic high (H) or
                low (L).
            VTERM - Specifies the termination voltage the digital pattern instrument applies during
                non-drive cycles when the termination mode is set to V :sub:`term`. The instrument
                applies the termination voltage through a 50 Ω parallel termination resistance.
            IOL or IOH - Specifies the current that the DUT sources (or sinks) to the active load
                while outputting a voltage above (or below) VCOM.
            VCOM - Specifies the voltage level at which the active load circuit switches between
                sourcing current and sinking current.

        Args:
            level_type_to_set (LevelTypeToSet): VIH or VIL or VOH or VOL or IOL or IOH or VCOM or
                VTERM
            per_site_value (typing.List[typing.List[float]]) : values to set per site
        """
        for ssc, settings in zip(self._sscs, per_site_value):
            channel_list_array, _, _ = _arrange_channels_per_site(ssc._channels, ssc._pins)
            for channel, setting in zip(channel_list_array, settings):
                if level_type_to_set == LevelTypeToSet.VIL:
                    ssc._session.channels[channel].vil = setting
                elif level_type_to_set == LevelTypeToSet.VIH:
                    ssc._session.channels[channel].vih = setting
                elif level_type_to_set == LevelTypeToSet.VOL:
                    ssc._session.channels[channel].vol = setting
                elif level_type_to_set == LevelTypeToSet.VOH:
                    ssc._session.channels[channel].voh = setting
                elif level_type_to_set == LevelTypeToSet.VTERM:
                    ssc._session.channels[channel].vterm = setting
                elif level_type_to_set == LevelTypeToSet.IOL:
                    ssc._session.channels[channel].active_load_iol = setting
                elif level_type_to_set == LevelTypeToSet.IOH:
                    ssc._session.channels[channel].active_load_ioh = setting
                elif level_type_to_set == LevelTypeToSet.VCOM:
                    ssc._session.channels[channel].active_load_vcom = setting
                ssc._session.commit()

    def configure_single_level(self, level_type_to_set: LevelTypeToSet, setting: float):
        """
        LevelTypeToSet
            VIH or VIL - Specifies the voltage that the digital pattern instrument will apply to the
                input of the DUT when the test instrument drives a logic high (1) or low (0).
            VOH or VOL - Specifies the output voltage from the DUT above (or below) which the
                comparator on the digital pattern test instrument interprets a logic high (H) or
                low (L).
            VTERM - Specifies the termination voltage the digital pattern instrument applies during
                non-drive cycles when the termination mode is set to V :sub:`term`. The instrument
                applies the termination voltage through a 50 Ω parallel termination resistance.
            IOL or IOH - Specifies the current that the DUT sources (or sinks) to the active load
                while outputting a voltage above (or below) VCOM.
            VCOM - Specifies the voltage level at which the active load circuit switches between
                sourcing current and sinking current.

        Args:
            level_type_to_set (LevelTypeToSet): VIH or VIL or VOH or VOL or IOL or IOH or VCOM or
                VTERM
            setting (float) : value to set
        """
        for ssc in self._sscs:
            ssc.cs_configure_single_level(level_type_to_set, setting)

    def configure_termination_mode(self, termination_mode: enums.TerminationMode):
        """
        Specifies the behavior of the pin during non-drive cycles.
        Args:
            termination_mode (enums.TerminationMode) : value defined as per the table below
        +-----------------------------+------------------------------------------------------------+
        | Defined Values:             |                                                            |
        +=============================+============================================================+
        | TerminationMode.ACTIVE_LOAD | Specifies that, for non-drive pin states (L, H, X, V, M, E)
                                        ,the active load is connected and the instrument sources or
                                        sinks a defined amount of current to load the DUT. The
                                        amount of current sourced by the instrument and therefore
                                        sunk by the DUT is specified by IOL. The amount of current
                                        sunk by the instrument and therefore sourced by the DUT is
                                        specified by IOH. The voltage at which the instrument
                                        changes between sourcing and sinking is specified by VCOM. |
        +-----------------------------+------------------------------------------------------------+
        | TerminationMode.VTERM       | Specifies that, for non-drive pin states (L, H, X, V, M, E)
                                        , the pin driver terminates the pin to the configured VTERM
                                        voltage through a 50 Ω impedance. VTERM is adjustable to
                                        allow for the pin to terminate at a set level. This is
                                        useful for instruments that might operate incorrectly if an
                                        instrument pin is unterminated and is allowed to float to
                                        any voltage level within the instrument voltage range. To
                                        address this issue, enable VTERM by configuring the VTERM
                                        pin level to the desired voltage and selecting the VTERM
                                        termination mode. Setting VTERM to 0 V and selecting the
                                        VTERM termination mode has the effect of connecting a 50 Ω
                                        termination to ground, which provides an effective 50 Ω
                                        impedance for the pin. This can be useful for improving
                                        signal integrity of certain DUTs by reducing reflections
                                        while the DUT drives the pin.                              |
        +-----------------------------+------------------------------------------------------------+
        | TerminationMode.HIGH_Z      | Specifies that, for non-drive pin states (L, H, X, V, M, E)
                                        , the pin driver is put in a high-impedance state and the
                                        active load is disabled.                                   |
        +-----------------------------+------------------------------------------------------------+
        """
        for ssc in self._sscs:
            ssc.cs_configure_termination_mode(termination_mode)

    def configure_time_set_compare_edge_per_site_per_pin(
        self,
        time_set: str,
        per_site_per_pin_compare_strobe: typing.List[typing.List[float]],
    ):
        """
        Configures the strobe edge time for the pins in the context. Use this method to modify time
        set values after applying a timing sheet with the apply_levels_and_timing method, or to
        create time sets programmatically without the use of timing sheets. This method does not
        modify the timing sheet file or the timing sheet contents that will be used in future calls
        to apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.
            per_site_per_pin_compare_strobe (typing.List[typing.List[float]]): Time when the
            comparison happens within a vector period.
        """
        for ssc, compare_strobes in zip(self._sscs, per_site_per_pin_compare_strobe):
            ssc.cs_configure_time_set_compare_edge_per_pin(time_set, compare_strobes)

    def configure_time_set_compare_edge_per_site(
        self,
        time_set: str,
        per_site_compare_strobe: typing.List[typing.List[float]],
    ):
        """
        Configures the strobe edge time for the pins in context. Use this method to modify time set
        values after applying a timing sheet with the apply_levels_and_timing method, or to create
        time sets programmatically without the use of timing sheets. This method does not modify the
        timing sheet file or the timing sheet contents that will be used in future calls to
        apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.

            per_site_compare_strobe (typing.List[typing.List[float]]): Time when the comparison
            happens within a vector period.
        """
        for ssc, compare_strobes in zip(self._sscs, per_site_compare_strobe):
            channel_list_array, _, _ = _arrange_channels_per_site(ssc._channels, ssc._pins)
            for channel, compare_strobe in zip(channel_list_array, compare_strobes):
                ssc._session.channels[channel].configure_time_set_compare_edges_strobe(
                    time_set, compare_strobe
                )

    def configure_time_set_compare_edge(self, time_set: str, compare_strobe: float):
        """
        Configures the strobe edge time for the specified pins. Use this method to modify time set
        values after applying a timing sheet with the apply_levels_and_timing method, or to create
        time sets programmatically without the use of timing sheets. This method does not modify the
        timing sheet file or the timing sheet contents that will be used in future calls to
        apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.
            compare_strobe (float in seconds): Time when the comparison happens within a vector
                period.
        """
        for ssc in self._sscs:
            ssc.cs_configure_time_set_compare_edge(time_set, compare_strobe)

    def configure_time_set_period(self, time_set: str, period: float):
        """
        Configures the period of a time set. Use this method to modify time set values after
        applying a timing sheet with the apply_levels_and_timing method, or to create time sets
        programmatically without the use of timing sheets. This method does not modify the timing
        sheet file or the timing sheet contents that will be used in future calls to
        apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.
            period (hightime.timedelta, datetime.timedelta, or float in seconds): Period for this
            time set, in seconds.

        Returns:
            period (float): configured period for this time set, in seconds
        """
        configured_period = period
        if configured_period > 40e-6:
            configured_period = 40e-6
        elif configured_period < 10e-9:
            configured_period = 10e-9
        for ssc in self._sscs:
            ssc._session.configure_time_set_period(time_set, configured_period)
        return configured_period

    def configure_voltage_levels(
        self,
        vil: float,
        vih: float,
        vol: float,
        voh: float,
        vterm: float,
    ):
        """
        Configures voltage levels for the pins in context.

        Args:
            vil (float): Voltage that the instrument will apply to the input of the DUT when the pin
                driver drives a logic low (0).
            vih (float): Voltage that the instrument will apply to the input of the DUT when the
                test instrument drives a logic high (1).
            vol (float): Output voltage below which the comparator on the pin driver interprets a
                logic low (L).
            voh (float): Output voltage above which the comparator on the pin driver interprets a
                logic high (H).
            vterm (float): Termination voltage the instrument applies during non-drive cycles when
                the termination mode is set to V\ :sub:`term`. The instrument applies the
                termination voltage through a 50 ohm parallel termination resistance.
        """
        for ssc in self._sscs:
            ssc._session.channels[ssc._channels].configure_voltage_levels(vil, vih, vol, voh, vterm)

    # End of Pin Levels and Timing #

    # PPMU #
    def ppmu_configure_aperture_time(self, aperture_time: float):
        """
        Specifies the measurement aperture time for the PPMU. The ppmu_aperture_time_units property
        sets the units of the PPMU aperture time.

        Args:
            aperture_time (float): measurement aperture time in ppmu_aperture_time_units
        """
        for ssc in self._sscs:
            ssc._session.channels[ssc._channels].ppmu_aperture_time = aperture_time

    def ppmu_configure_current_limit_range(self, current_limit_range: float):
        """
        Specifies the valid range, in amps, to which the current limit can be set while the PPMU
        forces voltage to the DUT. This property is applicable only when you set the
        ppmu_output_function property to DC Voltage.

        Args:
            current_limit_range (float): current limt range in amps
        """
        current_limit_range = abs(current_limit_range)
        for ssc in self._sscs:
            ssc._session.channels[ssc._channels].ppmu_current_limit_range = current_limit_range

    def ppmu_configure_voltage_limits(self, voltage_limit_high: float, voltage_limit_low: float):
        """
        Specifies the maximum voltage limit, or high clamp voltage (V :sub:`CH` ) and  the minimum
        voltage limit, or low clamp voltage (V :sub:`CL` ),in volts, at the pin when the PPMU forces
        current to the DUT. This property is applicable only when you set the ppmu_output_function
        property to DC Current.

        Args:
            voltage_limit_high (float): high clamp voltage
            voltage_limit_low (float): low clamp voltage
        """
        for ssc in self._sscs:
            ssc._session.channels[ssc._channels].ppmu_voltage_limit_high = voltage_limit_high
            ssc._session.channels[ssc._channels].ppmu_voltage_limit_low = voltage_limit_low

    def ppmu_measure(self, measurement_type: enums.PPMUMeasurementType):
        """
        Instructs the PPMU to measure voltage or current. This method can be called to take a
        voltage measurement even if the pin method is not set to PPMU.

        Args:
            measurement_type (enums.PPMUMeasurementType): Parameter that specifies whether the PPMU
            measures voltage or current from the DUT.
                -   PPMUMeasurementType.CURRENT: The PPMU measures current from the DUT.
                -   PPMUMeasurementType.VOLTAGE: The PPMU measures voltage from the DUT.

        Returns:
            measurements (list of float): The returned array of measurements in the order you
            specify in the repeated capabilities. If a site is disabled, the method does not return
            data for that site. You can also use the get_pin_results_pin_information method to
            obtain a sorted list of returned sites and channels.
        """
        per_instrument_measurements: typing.List[typing.List[float]] = []
        for ssc in self._sscs:
            per_instrument_measurements.append(
                ssc._session.channels[ssc._channels].ppmu_measure(measurement_type)
            )
        return per_instrument_measurements

    def ppmu_source_current(self, current_level: float, current_level_range: float = 0):
        """
        selects the PPMU method and applies current level and range.
        Starts sourcing current from the PPMU on all channels in the context.

        Args:
            current_level (float): _description_
            current_level_range (float, optional): _description_. Defaults to 0.
        """
        for ssc in self._sscs:
            ssc.cs_ppmu_source_current(current_level, current_level_range)

    def ppmu_source_voltage_per_site_per_pin(
        self,
        current_limit_range: float,
        per_site_per_pin_source_voltages: typing.List[typing.List[float]],
    ):
        """
        Configures the PPMU to outputfunction as Voltage and starts sourcing voltage from the PPMU.
        configures the current limit range for sourcing voltage.

        Args:
            current_limit_range (float): common current limit for all session channels
            per_site_per_pin_source_voltages (typing.List[typing.List[float]]): list of source
            voltage for each site for each pin
        """
        current_limit_range = abs(current_limit_range)
        for ssc, source_voltages in zip(self._sscs, per_site_per_pin_source_voltages):
            ssc._session.channels[
                ssc._channels
            ].ppmu_output_function = enums.PPMUOutputFunction.VOLTAGE
            ssc._session.channels[ssc._channels].ppmu_current_limit_range = current_limit_range
            channels, _, _ = _channel_list_to_pins(ssc._channels)
            for channel, source_voltage in zip(channels, source_voltages):
                ssc._session.channels[channel].ppmu_voltage_level = source_voltage
            ssc._session.channels[ssc._channels].ppmu_source()

    def ppmu_source_voltage_per_site(
        self,
        current_limit_range: float,
        per_site_source_voltages: typing.List[typing.List[float]],
    ):
        """
        Configures the PPMU to outputfunction as Voltage and starts sourcing voltage from the PPMU.
        configures the current limit range for sourcing voltage.

        Args:
            current_limit_range (float): common current limit for all session channels
            per_site_source_voltages (typing.List[typing.List[float]]): list of source voltage for
            each site
        """
        current_limit_range = abs(current_limit_range)
        for ssc, source_voltages in zip(self._sscs, per_site_source_voltages):
            ssc._session.channels[
                ssc._channels
            ].ppmu_output_function = enums.PPMUOutputFunction.VOLTAGE
            ssc._session.channels[ssc._channels].ppmu_current_limit_range = current_limit_range
            channel_list_array, _, _ = _arrange_channels_per_site(ssc._channels, ssc._pins)
            for channel, source_voltage in zip(channel_list_array, source_voltages):
                ssc._session.channels[channel].ppmu_voltage_level = source_voltage
            ssc._session.channels[ssc._channels].ppmu_source()

    def ppmu_source_voltage(self, voltage_level: float, current_limit_range: float):
        """
        Current limit is not configured here
        The PXIe-6570 and PXIe-6571 do not support current limits in PPMU voltage mode:
        http://zone.ni.com/reference/en-XX/help/375145e/nidigitalpropref/pnidigital_ppmucurrentlimit/
        """
        current_limit_range = abs(current_limit_range)
        for ssc in self._sscs:
            ssc.cs_ppmu_source_voltage(voltage_level, current_limit_range)

    def ppmu_source(self):
        """
        Starts sourcing voltage or current from the PPMU. This method automatically selects the PPMU
        method. Changes to PPMU source settings do not take effect until you call this method. If
        you modify source settings after you call this method, you must call this method again for
        changes in the configuration to take effect.
        """
        for ssc in self._sscs:
            ssc.cs_ppmu_source()

    # End of PPMU #

    # Sequencer Flags and Registers #
    def read_sequencer_flag(self, sequencer_flag: enums.SequencerFlag):
        """
        Reads the state of a pattern sequencer flag. Use pattern sequencer flags to coordinate
        execution between the pattern sequencer and a runtime test program.

        Args:
            sequencer_flag (enums.SequencerFlag): The pattern sequencer flag you want to read.

                -   SequencerFlag.FLAG0 ("seq_flag0"): Reads pattern sequencer flag 0.
                -   SequencerFlag.FLAG1 ("seq_flag1"): Reads pattern sequencer flag 1.
                -   SequencerFlag.FLAG2 ("seq_flag2"): Reads pattern sequencer flag 2.
                -   SequencerFlag.FLAG3 ("seq_flag3"): Reads pattern sequencer flag 3.

        Returns:
            values (list of bool): A Boolean that indicates the state of the pattern sequencer flag
            you specify from different instrument sessions.
        """
        per_instrument_state: typing.List[bool] = []
        for ssc in self._sscs:
            per_instrument_state.append(ssc._session.read_sequencer_flag(sequencer_flag))
        return per_instrument_state

    def read_sequencer_register(self, sequencer_register: enums.SequencerRegister):
        """
        Reads the value of a pattern sequencer register. Use pattern sequencer registers to pass
        numeric values between the pattern sequencer and a runtime test program. For example, you
        can use this method to read a register modified by the write_reg opcode during a pattern
        burst.

        Args:
            sequencer_register (enums.SequencerRegister): The sequencer register to read from.

                -   SequencerRegister.REGISTER0 ("reg0"): Reads sequencer register 0.
                -   SequencerRegister.REGISTER1 ("reg1"): Reads sequencer register 1.
                -   SequencerRegister.REGISTER2 ("reg2"): Reads sequencer register 2.
                -   SequencerRegister.REGISTER3 ("reg3"): Reads sequencer register 3.
                -   SequencerRegister.REGISTER4 ("reg4"): Reads sequencer register 4.
                -   SequencerRegister.REGISTER5 ("reg5"): Reads sequencer register 5.
                -   SequencerRegister.REGISTER6 ("reg6"): Reads sequencer register 6.
                -   SequencerRegister.REGISTER7 ("reg7"): Reads sequencer register 7.
                -   SequencerRegister.REGISTER8 ("reg8"): Reads sequencer register 8.
                -   SequencerRegister.REGISTER9 ("reg9"): Reads sequencer register 9.
                -   SequencerRegister.REGISTER10 ("reg10"): Reads sequencer register 10.
                -   SequencerRegister.REGISTER11 ("reg11"): Reads sequencer register 11.
                -   SequencerRegister.REGISTER12 ("reg12"): Reads sequencer register 12.
                -   SequencerRegister.REGISTER13 ("reg13"): Reads sequencer register 13.
                -   SequencerRegister.REGISTER14 ("reg14"): Reads sequencer register 14.
                -   SequencerRegister.REGISTER15 ("reg15"): Reads sequencer register 15.

        Returns:
            values (list of int): Value read from the sequencer register from different instrument
            sessions.
        """
        per_instrument_register_values: typing.List[int] = []
        for ssc in self._sscs:
            per_instrument_register_values.append(
                ssc._session.read_sequencer_register(sequencer_register)
            )
        return per_instrument_register_values

    def write_sequencer_flag(
        self,
        sequencer_flag: enums.SequencerFlag,
        state: bool = True,
    ):
        """
        Writes the state of a pattern sequencer flag. Use pattern sequencer flags to coordinate
        execution between the pattern sequencer and a runtime test program.

        Args:
            sequencer_flag (enums.SequencerFlag): The pattern sequencer flag to write.

                -   SequencerFlag.FLAG0 ("seq_flag0"): Writes pattern sequencer flag 0.
                -   SequencerFlag.FLAG1 ("seq_flag1"): Writes pattern sequencer flag 1.
                -   SequencerFlag.FLAG2 ("seq_flag2"): Writes pattern sequencer flag 2.
                -   SequencerFlag.FLAG3 ("seq_flag3"): Writes pattern sequencer flag 3.

            state (bool, optional): A Boolean that assigns a state to the pattern sequencer flag you
            specify.Defaults to True.
        """
        for ssc in self._sscs:
            ssc._session.write_sequencer_flag(sequencer_flag, state)

    def write_sequencer_register(
        self,
        sequencer_register: enums.SequencerRegister,
        value: int = 0,
    ):
        """
        Writes a value to a pattern sequencer register. Use pattern sequencer registers to pass
        numeric values between the pattern sequencer and a runtime test program.

        Args:
            sequencer_register (enums.SequencerRegister): The sequencer register you want to write
            to.
                -   SequencerRegister.REGISTER0 ("reg0"): Writes sequencer register 0.
                -   SequencerRegister.REGISTER1 ("reg1"): Writes sequencer register 1.
                -   SequencerRegister.REGISTER2 ("reg2"): Writes sequencer register 2.
                -   SequencerRegister.REGISTER3 ("reg3"): Writes sequencer register 3.
                -   SequencerRegister.REGISTER4 ("reg4"): Writes sequencer register 4.
                -   SequencerRegister.REGISTER5 ("reg5"): Writes sequencer register 5.
                -   SequencerRegister.REGISTER6 ("reg6"): Writes sequencer register 6.
                -   SequencerRegister.REGISTER7 ("reg7"): Writes sequencer register 7.
                -   SequencerRegister.REGISTER8 ("reg8"): Writes sequencer register 8.
                -   SequencerRegister.REGISTER9 ("reg9"): Writes sequencer register 9.
                -   SequencerRegister.REGISTER10 ("reg10"): Writes sequencer register 10.
                -   SequencerRegister.REGISTER11 ("reg11"): Writes sequencer register 11.
                -   SequencerRegister.REGISTER12 ("reg12"): Writes sequencer register 12.
                -   SequencerRegister.REGISTER13 ("reg13"): Writes sequencer register 13.
                -   SequencerRegister.REGISTER14 ("reg14"): Writes sequencer register 14.
                -   SequencerRegister.REGISTER15 ("reg15"): Writes sequencer register 15.

            value (int, optional): The value you want to write to the register. Defaults to 0.
        """
        for ssc in self._sscs:
            ssc._session.write_sequencer_register(sequencer_register, value)

    # End of Sequencer Flags and Registers #

    # Source and Capture Waveforms #
    def fetch_capture_waveform(
        self,
        waveform_name: str,
        samples_to_read: int,
        timeout: float = 10,
    ):
        """
        Returns dictionary where each key is a site number and value is a collection of digital
        states representing capture waveform data

        Args:
            waveform_name (str): Waveform name you create with the create capture waveform method.
                Use the waveform_name parameter with capture_start opcode in your pattern.
            samples_to_read (int): Number of samples to fetch.
            timeout (float, optional): Maximum time (in seconds) allowed for this method to
                complete. If this method does not complete within this time interval, this method
                returns an error. Defaults to 10.

        Returns:
            per instrument waveform capture ({ int: memoryview of array.array of unsigned int, int:
            memoryview of array.array of unsigned int, ... }): Dictionary where each key is a site
            number and value is a collection of digital states representing capture waveform data
        """
        per_instrument_capture: typing.List[typing.List[typing.List[int]]] = []
        for ssc in self._sscs:
            waveforms = ssc._session.sites[ssc._pins].fetch_capture_waveform(
                waveform_name, samples_to_read, timeout
            )
            per_instrument_capture.append([list(waveforms[i]) for i in waveforms.keys()])
        return per_instrument_capture

    def write_source_waveform_broadcast(
        self,
        waveform_name: str,
        waveform_data: typing.List[int],
        expand_to_minimum_size: bool = False,
        minimum_size: int = 128,
    ):
        """
        Writes the same waveform data to all sites. Use this write method if you set the
        data_mapping parameter of the create source waveform method to SourceDataMapping.BROADCAST.

        Args:
            waveform_name (str): The name to assign to the waveform. Use the waveform_name with
                source_start opcode in your pattern.

            waveform_data (list of int): 1D array of samples to use as source data to apply to all
                sites.
            expand_to_minimum_size (bool, optional): decides to expand the waveform data or not.
                Defaults to False.
            minimum_size (int, optional): minimum size to expand the waveform data. Defaults to 128.
        """
        if minimum_size > len(waveform_data) and expand_to_minimum_size:
            initialized_array = [0 for _ in range(minimum_size)]
            for i in range(len(waveform_data)):
                initialized_array[i] = waveform_data[i]
            waveform_data = initialized_array
        for ssc in self._sscs:
            ssc._session.write_source_waveform_broadcast(waveform_name, waveform_data)

    def write_source_waveform_site_unique(
        self,
        waveform_name: str,
        per_instrument_waveforms: typing.List[typing.List[typing.List[int]]],
        expand_to_minimum_size: bool = False,
        minimum_size: int = 128,
    ):
        """
        Writes one waveform per site. Use this write method if you set the parameter of the create
        source waveform method to Site Unique.

        Args:
            waveform_name (str): The name to assign to the waveform. Use the waveform_name with
                source_start opcode in your pattern.
            per_instrument_waveforms (typing.List[typing.List[typing.List[int]]]): list of
                waveform_data ({ int: basic sequence of unsigned int, int: basic sequence of
                unsigned int, ... }): Dictionary where each key is a site number and value is a
                collection of samples to use as source data
            expand_to_minimum_size (bool, optional): if set to true the array of waveform will be of
                "minimum_size" parameter with zeros padded as required. Defaults to False.
            minimum_size (int, optional): specifices the minimum length of each waveform per site.
                Defaults to 128.
        """
        for ssc, per_instrument_waveform in zip(self._sscs, per_instrument_waveforms):
            rows, cols = numpy.shape(per_instrument_waveform)
            site_numbers, _ = _site_list_to_site_numbers(ssc._pins)
            if minimum_size > cols and expand_to_minimum_size:
                initialized_array = [
                    [0 for _ in range(minimum_size)] for _ in range(len(site_numbers))
                ]
                for row in range(rows):
                    for col in range(cols):
                        initialized_array[row][col] = per_instrument_waveform[row][col]
                per_instrument_waveform = initialized_array
            waveform_data = {}
            for site_number, waveform in zip(site_numbers, per_instrument_waveform):
                waveform_data[site_number] = waveform
            ssc._session.write_source_waveform_site_unique(waveform_name, waveform_data)

    # End of Source and Capture Waveforms #

    # Static #
    def read_static(self):
        """
        Reads the current state of comparators for pins you specify in the repeated capabilities.
        If there are uncommitted changes to levels or the termination mode, this method commits
        the changes to the pins.

        Returns:
            data (list [list of enums.PinState]): The returned array of pin states read from the
            channels in the repeated capabilities. Data is returned as per the order you specify in
            the repeated capabilities. If a site is disabled, the method does not return data for
            that site. You can also use the get_pin_results_pin_information method to obtain a
            sorted list of returned sites and channels.

                -   PinState.L: The comparators read a logic low pin state.
                -   PinState.H: The comparators read a logic high pin state.
                -   PinState.M: The comparators read a mid-band pin state.
                -   PinState.V: The comparators read a value that is above VOH and below VOL,
                                which can occur when you set VOL higher than VOH.
        """
        return [ssc.cs_read_static() for ssc in self._sscs]

    def write_static(self, state: enums.WriteStaticPinState, auto_select=True):
        """
        Writes a static state to the specified pins. The selected pins remain in the specified state
        until the next pattern burst or call to this method. If there are uncommitted changes to
        levels or the termination mode, this method commits the changes to the pins. This method
        does not change the selected pin method. If you write a static state to a pin that does not
        have the Digital method selected, the new static state is stored by the instrument, and
        affects the state of the pin the next time you change the selected method to Digital.

        Args:
            state (enums.WriteStaticPinState): Parameter that specifies one of the following digital
            states to assign to each pin per site.

                -   WriteStaticPinState.ZERO: Specifies to drive low.
                -   WriteStaticPinState.ONE: Specifies to drive high.
                -   WriteStaticPinState.X: Specifies to not drive.

            auto_select=True, specifies this function to configure the output function as digital
            automatically.auto_select=False, if the pin is explicitly configured as digital already
            with the tsm_object.ssc.select_function().Without configuring as digital and auto_select
            as false, this function will not work as expected.
        """
        for ssc in self._sscs:
            ssc.cs_write_static(state, auto_select)

    def write_static_per_site_per_pin(
        self,
        per_site_per_pin_state: typing.List[typing.List[enums.WriteStaticPinState]],
        auto_select=True,
    ):
        """
        Writes a static state to the specified pins per site per pin. The selected pins remain in
        the specified state until the next pattern burst or call to this method. If there are
        uncommitted changes to levels or the termination mode, this method commits the changes to
        the pins. This method does not change the selected pin method. If you write a static state
        to a pin that does not have the Digital method selected, the new static state is stored by
        the instrument, and affects the state of the pin the next time you change the selected
        method to Digital.

        Args:
            per_site_per_pin_state (typing.List[typing.List[enums.WriteStaticPinState]]): Parameter
            that specifies one of the following digital states to assign to each pin per site.

                -   WriteStaticPinState.ZERO: Specifies to drive low.
                -   WriteStaticPinState.ONE: Specifies to drive high.
                -   WriteStaticPinState.X: Specifies to not drive.
            auto_select=True, specifies this function to configure the output function as digital
            automatically.auto_select=False, if the pin is explicitly configured as digital already
            with the tsm_object.ssc.select_function().Without configuring as digital and auto_select
            as false, this function will not work as expected.
        """
        for ssc, states in zip(self._sscs, per_site_per_pin_state):
            channels, _, _ = _channel_list_to_pins(ssc._channels)
            for channel, state in zip(channels, states):
                if auto_select:
                    ssc._session.channels[channel].select_function(enums.SelectedFunction.DIGITAL)
                ssc._session.channels[channel].write_static(state)

    def write_static_per_site(
        self, per_site_state: typing.List[typing.List[enums.WriteStaticPinState]], auto_select=True
    ):
        """
        Writes a static state per site. The selected pins remain in the specified state until the
        next pattern burst or call to this method. If there are uncommitted changes to levels or the
        termination mode, this method commits the changes to the pins. This method does not change
        the selected pin method. If you write a static state to a pin that does not have the Digital
        method selected, the new static state is stored by the instrument, and affects the state of
        the pin the next time you change the selected method to Digital.

        Args:
            per_site_state (typing.List[typing.List[enums.WriteStaticPinState]]): Parameter that
            specifies one of the following digital states to assign to each pin per site.

                -   WriteStaticPinState.ZERO: Specifies to drive low.
                -   WriteStaticPinState.ONE: Specifies to drive high.
                -   WriteStaticPinState.X: Specifies to not drive.
            auto_select=True, specifies this function to configure the output function as digital
            automatically.auto_select=False, if the pin is explicitly configured as digital already
            with the tsmobj.ssc.select_function().Without configuring as digital and auto_select as
            false, this function will not work as expected.
        """
        for ssc, states in zip(self._sscs, per_site_state):
            channel_list_array, _, _ = _arrange_channels_per_site(ssc._channels, ssc._pins)
            for channel, state in zip(channel_list_array, states):
                if auto_select:
                    ssc._session.channels[channel].select_function(enums.SelectedFunction.DIGITAL)
                ssc._session.channels[channel].write_static(state)
        # End of Static #

        # Trigger #

    def clear_start_trigger_signal(self):
        """
        Disables the Start trigger. Pattern bursting starts immediately after you call the init
        method or the burst_pattern method.
        """
        for ssc in self._sscs:
            ssc.cs_clear_start_trigger_signal()

    def configure_trigger_signal(
        self, source: str, edge: enums.DigitalEdge = enums.DigitalEdge.RISING
    ):
        """
        Specifies the source terminal for the Start trigger. configures the start_trigger_type
        property as Digital Edge.

        Args:
            source (str): You can specify source terminals in one of two ways. If the digital
            pattern instrument is named Dev1 and your terminal is PXI_Trig0, you can specify the
            terminal with the fully qualified terminal name, /Dev1/PXI_Trig0, or with the shortened
            terminal name, PXI_Trig0. The source terminal can also be a terminal from another
            device, in which case the NI-Digital Pattern Driver automatically finds a route (if one
            is available) from that terminal to the input terminal (going through a physical PXI
            backplane trigger line). For example, you can set the source terminal on Dev1 to be
            /Dev2/StartTrigger.

            +-----------------+--------------------+
            | Defined Values: |                    |
            +=================+====================+
            | PXI_Trig0       | PXI trigger line 0 |
            +-----------------+--------------------+
            | PXI_Trig1       | PXI trigger line 1 |
            +-----------------+--------------------+
            | PXI_Trig2       | PXI trigger line 2 |
            +-----------------+--------------------+
            | PXI_Trig3       | PXI trigger line 3 |
            +-----------------+--------------------+
            | PXI_Trig4       | PXI trigger line 4 |
            +-----------------+--------------------+
            | PXI_Trig5       | PXI trigger line 5 |
            +-----------------+--------------------+
            | PXI_Trig6       | PXI trigger line 6 |
            +-----------------+--------------------+
            | PXI_Trig7       | PXI trigger line 7 |
            +-----------------+--------------------+

            edge (enums.DigitalEdge, optional): rising or falling edge. Defaults to
            enums.DigitalEdge.RISING.
        """
        for ssc in self._sscs:
            ssc.cs_configure_trigger_signal(source, edge)

    def export_opcode_trigger_signal(self, signal_id: str, output_terminal: str = ""):
        """
        Specifies the destination terminal for exporting the Pattern Opcode Event. Terminals can be
        specified in one of two ways. If the digital pattern instrument is named Dev1 and your
        terminal is PXI_Trig0, you can specify the terminal with the fully qualified terminal name,
        /Dev1/PXI_Trig0, or with the shortened terminal name, PXI_Trig0.

        +-----------------+--------------------+
        | Defined Values: |                    |
        +=================+====================+
        | PXI_Trig0       | PXI trigger line 0 |
        +-----------------+--------------------+
        | PXI_Trig1       | PXI trigger line 1 |
        +-----------------+--------------------+
        | PXI_Trig2       | PXI trigger line 2 |
        +-----------------+--------------------+
        | PXI_Trig3       | PXI trigger line 3 |
        +-----------------+--------------------+
        | PXI_Trig4       | PXI trigger line 4 |
        +-----------------+--------------------+
        | PXI_Trig5       | PXI trigger line 5 |
        +-----------------+--------------------+
        | PXI_Trig6       | PXI trigger line 6 |
        +-----------------+--------------------+
        | PXI_Trig7       | PXI trigger line 7 |
        +-----------------+--------------------+
        Args:
            signal_id (str): pxi trigger line name
            output_terminal (str, optional): _description_. Defaults to "".
        """
        for ssc in self._sscs:
            ssc.cs_export_opcode_trigger_signal(signal_id, output_terminal)

    # End of Trigger #

    def filter_sites(self, desired_sites: typing.List[int]):
        """
        filter  the sites specified in the current TSMObject

        Args:
            desired_sites (list of int): sites

        Returns:
            SSC: list of sessions sites and channels
        """
        sscs_new: typing.List[_NIDigitalSSC] = []
        for ssc in self._sscs:
            channel_list_array, site_list_array, site_numbers = _arrange_channels_per_site(
                ssc._channels, ssc._pins
            )
            channel_list: typing.List[str] = []
            site_list: typing.List[str] = []
            for _channel_list, _site_list, site_number in zip(
                channel_list_array, site_list_array, site_numbers
            ):
                if site_number in desired_sites:
                    channel_list.append(_channel_list)
                    site_list.append(_site_list)
            if site_list:
                sscs_new.append(
                    _NIDigitalSSC(ssc._session, ",".join(channel_list), ",".join(site_list))
                )
        nidigital_tsm = _NIDigitalTSM(sscs_new)
        return nidigital_tsm

    def initiate(self):
        """
         Starts bursting the pattern configured by start_label, causing the NI-Digital session to be
         committed. To stop the pattern burst, call abort. If keep alive pattern is bursting when
         abort is called or upon exiting the context manager, keep alive pattern will not be
         stopped. To stop the keep alive pattern, call abort_keep_alive.

        Note:
        This method will return a Python context manager that will initiate on entering and abort on
        exit.
        """
        for ssc in self._sscs:
            ssc._session.initiate()

    def calculate_per_instrument_per_site_to_per_site_lut(self, sites: typing.List[int]):
        """
        computes per instrument per site to per site lookup table

        Args:
            sites (typing.List[int]): list of site numbers

        Returns:
            list: per_instrument_per_site_to_per_site_lut
        """
        per_instrument_per_site_to_per_site_lut: typing.List[Location1DArray] = []
        for ssc in self._sscs:
            site_numbers, _ = _site_list_to_site_numbers(ssc._pins)
            array: typing.List[Location1DArray] = []
            for site_number in site_numbers:
                array.append(Location1DArray([sites.index(site_number)]))
            per_instrument_per_site_to_per_site_lut += array
        return per_instrument_per_site_to_per_site_lut

    def calculate_per_instrument_to_per_site_lut(self, sites: typing.List[int]):
        """
        computes the per instrument to per site lookup table

        Args:
            sites (typing.List[int]): list of site numbers

        Returns:
            list: per_instrument_to_per_site_lut
        """
        per_instrument_to_per_site_lut: typing.List[Location1DArray] = []
        for ssc in self._sscs:
            site_numbers, _ = _site_list_to_site_numbers(ssc._pins)
            array: typing.List[int] = []
            for site_number in site_numbers:
                array.append(sites.index(site_number))
            per_instrument_to_per_site_lut.append(Location1DArray(array))
        return per_instrument_to_per_site_lut

    def calculate_per_instrument_to_per_site_per_pin_lut(
        self, sites: typing.List[int], pins: typing.List[str]
    ):
        """
        computes per instrument to per site per pin lookup table

        Args:
            sites (typing.List[int]): list of site numbers
            pins (typing.List[str]): list of pin names

        Returns:
            list: per_instrument_to_per_site_per_pin_lut
        """
        per_instrument_to_per_site_per_pin_lut: typing.List[Location2DArray] = []
        for ssc in self._sscs:
            _, _pins, _sites = _channel_list_to_pins(ssc._channels)
            array: typing.List[Location2D] = []
            for pin, site in zip(_pins, _sites):
                array.append(Location2D(sites.index(site), pins.index(pin)))
            per_instrument_to_per_site_per_pin_lut.append(Location2DArray(array))
        return per_instrument_to_per_site_per_pin_lut

    def calculate_per_site_per_pin_to_per_instrument_lut(
        self, sites: typing.List[int], pins: typing.List[str]
    ):
        """
        computes the per site per pin to per instrument lookup table

        Args:
            sites (typing.List[int]): list of site numbers
            pins (typing.List[str]): list of pin names

        Returns:
            tuple: per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        """
        max_sites_on_instrument = 0
        i = 0
        location_2d_array: typing.List[Location2D] = []
        pins_sites_array: typing.List[typing.Any] = []
        per_site_per_pin_to_per_instrument_lut: typing.List[typing.List[Location2D]] = []
        for _ssc in self._sscs:
            _, _pins, _sites = _channel_list_to_pins(_ssc._channels)
            pins_sites_array += list(map(list, zip(_pins, _sites)))
            max_sites_on_instrument = max(max_sites_on_instrument, len(_pins))
            location_2d_array += [Location2D(i, j) for j in range(len(_pins))]
            i += 1
        instrument_count = i
        for site in sites:
            array: typing.List[Location2D] = []
            for pin in pins:
                index = pins_sites_array.index([pin, site])
                array.append(location_2d_array[index])
            per_site_per_pin_to_per_instrument_lut.append(array)
        return (
            per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        )

    def calculate_per_site_to_per_instrument_lut(self, sites: typing.List[int]):
        """
        computes the per site to per instrument lookup table.

        Args:
            sites (typing.List[int]): list of site numbers

        Returns:
            tuple: per_site_to_per_instrument_lut, instrument_count, max_sites_on_instrument
        """
        max_sites_on_instrument = 0
        i = 0
        location_2d_array: typing.List[Location2D] = []
        sites_array: typing.List[int] = []
        per_site_to_per_instrument_lut: typing.List[Location2D] = []
        for ssc in self._sscs:
            site_numbers, _ = _site_list_to_site_numbers(ssc._pins)
            sites_array += site_numbers
            max_sites_on_instrument = max(max_sites_on_instrument, len(site_numbers))
            location_2d_array += [Location2D(i, j) for j in range(len(site_numbers))]
            i += 1
        instrument_count = i
        for site in sites:
            index = sites_array.index(site)
            per_site_to_per_instrument_lut.append(location_2d_array[index])
        return per_site_to_per_instrument_lut, instrument_count, max_sites_on_instrument

    def get_properties(self):
        """
        Returns list of session properties i.e. Voh, Vol, Vih, Vil, Vterm,
        frequency_counter_measurement_time in a named tuple format

        Returns:
            list of session_property: list of Named tuple of session property
        """
        return [ssc.cs_get_properties() for ssc in self._sscs]


class TSMDigital:
    """
    class that stores TSMDigital operations
    """

    def __init__(
        self,
        pin_query_context: typing.Any,
        ssc: _NIDigitalTSM,
        sites: typing.List[int],
        pins: typing.List[str],
    ):
        """
        constructor for TSMDigital to store sessions, sites and pins for the pin query context

        Args:
            pin_query_context (typing.Any): _description_
            ssc (_NIDigitalTSM): _description_
            sites (typing.List[int]): _description_
            pins (typing.List[str]): _description_
        """
        self.pin_query_context = pin_query_context
        self.ssc = ssc
        self.sites = sites
        self.pins = pins

    def frequency_counter_measure_frequency(self):
        """
        Measures the frequency on all the channel(s) over the specified measurement time.

        Returns:
            list [ list[float]]: measurement frequencies per site per pin

        Returns:
            per_site_per_pin_frequency_measurements: list of lists of float
        """
        initialized_array = [[0.0 for _ in self.pins] for _ in self.sites]
        per_instrument_to_per_site_per_pin_lut = (
            self.ssc.calculate_per_instrument_to_per_site_per_pin_lut(self.sites, self.pins)
        )
        per_instrument_frequencies = self.ssc.frequency_counter_measure_frequency()
        per_site_per_pin_frequency_measurements = _apply_lut_per_instrument_to_per_site_per_pin(
            initialized_array,
            per_instrument_to_per_site_per_pin_lut,
            per_instrument_frequencies,
        )
        return per_site_per_pin_frequency_measurements

    def get_hram_configuration(self):
        """
        gets the current HRAM settings and HRAM trigger settings in a tuple of lists format

        Returns:
            HRAMConfiguration(named tuple): contains HRAM Cycles to acquire,pretrigger samples, max
            samples to acquire per site, is number of samples finite, buffer size per site, trigger
            type, cycle number, pattern label, cycle offset, vector offset
        """
        (
            per_instrument_cycles_to_acquire,
            per_instrument_pretrigger_samples,
            per_instrument_max_samples_to_acquire_per_site,
            per_instrument_number_of_samples_is_finite,
            per_instrument_buffer_size_per_site,
        ) = self.ssc.get_hram_settings()
        (
            per_instrument_triggers_type,
            per_instrument_cycle_number,
            per_instrument_pattern_label,
            per_instrument_cycle_offset,
            per_instrument_vector_offset,
        ) = self.ssc.get_hram_trigger_settings()
        # Assumes all instruments have the same settings
        hram_configuration: HRAMConfiguration = HRAMConfiguration()
        hram_configuration.finite_samples = per_instrument_number_of_samples_is_finite[-1]
        hram_configuration.trigger_type = per_instrument_triggers_type[-1]
        hram_configuration.cycle_number = per_instrument_cycle_number[-1]
        hram_configuration.pattern_label = per_instrument_pattern_label[-1]
        hram_configuration.vector_offset = per_instrument_vector_offset[-1]
        hram_configuration.cycle_offset = per_instrument_cycle_offset[-1]
        hram_configuration.cycles_to_acquire = per_instrument_cycles_to_acquire[-1]
        hram_configuration.pretrigger_samples = per_instrument_pretrigger_samples[-1]
        hram_configuration.buffer_size_per_site = per_instrument_buffer_size_per_site[-1]
        hram_configuration.max_samples_to_acquire_per_site = (
            per_instrument_max_samples_to_acquire_per_site[-1]
        )
        return hram_configuration

    def log_hram_results(
        self,
        per_site_cycle_information: typing.List[typing.List[HistoryRAMCycleInformation]],
        pattern_name: str,
        destination_dir: str,
    ):
        """
        stores the HRAM results from every site into multiple log files

        Args:
            per_site_cycle_information (typing.List[typing.List[HistoryRAMCycleInformation]]): HRAM
                results
            pattern_name (str): pattern name used for bursting
            destination_dir (str): destination folder under which the log files are created.

        Returns:
            files_generated (list of filenames): returns the list of log file names
        """
        if not os.path.exists(destination_dir):
            os.mkdir(destination_dir)
        os.chdir(destination_dir)
        files_generated: typing.List[str] = []
        for cycle_informations, site_number in zip(per_site_cycle_information, self.sites):
            results: typing.List[typing.List[typing.Any]] = []
            if not cycle_informations or all(
                [
                    not cycle_information.per_pin_pass_fail
                    for cycle_information in cycle_informations
                ]
            ):
                results.append(["PATTERN PASSED - NO FAILURES"])
            else:
                for cycle_information in cycle_informations:
                    results.append(
                        [
                            str(cycle_information.vector_number),
                            cycle_information.time_set_name,
                            str(cycle_information.cycle_number),
                            str(cycle_information.scan_cycle_number),
                            str(
                                (lambda x: "P" if x else "F")(
                                    all(cycle_information.per_pin_pass_fail)
                                )
                            ),
                            "{" + ",".join(self.pins) + "}",
                            "{"
                            + ",".join(
                                [
                                    (lambda x: "P" if x is True else "F")(value)
                                    for value in cycle_information.per_pin_pass_fail
                                ]
                            )
                            + "}",
                            "{"
                            + ",".join(
                                [str(value) for value in cycle_information.expected_pin_states]
                            )
                            + "}",
                            "{"
                            + ",".join(
                                [str(value) for value in cycle_information.actual_pin_states]
                            )
                            + "}",
                        ]
                    )
                results.insert(
                    0,
                    [
                        "Vector",
                        "Timeset",
                        "Cycle",
                        "Scan Cycle",
                        "Pass/Fail",
                        "Pin List",
                        "Per Pin Pass/Fail",
                        "Expected Pin States",
                        "Actual Pin States",
                    ],
                )
            filename = (
                "HRAM_Results_site"
                + str(site_number)
                + "_"
                + datetime.now().strftime("%d-%b-%Y-%H-%M-%S")
                + ".csv"
            )
            files_generated.append(filename)
            file_handle = open(filename, "w")
            for row in results:
                for col in row:
                    file_handle.write("%s\t" % col)
                file_handle.write("\n")
            file_handle.close()
        return files_generated

    def stream_hram_results(self):
        """
        Returns the pattern information acquired for the specified cycles.If the pattern is using
        the edge multiplier feature, cycle numbers represent tester cycles, each of which may
        consist of multiple DUT cycles. When using pins with mixed edge multipliers, pins may return
        PinState.PIN_STATE_NOT_ACQUIRED for DUT cycles where those pins do not have edges defined.
        Site number on which to retrieve pattern information must be specified via sites repeated
        capability.The method returns an error if more than one site is specified. Pins for which to
        retrieve pattern information must be specified via pins repeated capability.If pins are not
        specified, pin list from the pattern containing the start label is used. Call
        get_pattern_pin_names with the start label to retrieve the pins associated with the pattern
        burst:

        Note:
        Before bursting a pattern, you must configure the History RAM trigger and specify which
        cycles to acquire.

        history_ram_trigger_type should be used to specify the trigger condition on which History
        RAM starts acquiring pattern information.

        If History RAM trigger is configured as HistoryRAMTriggerType.CYCLE_NUMBER,
        cycle_number_history_ram_trigger_cycle_number should be used to specify the cycle number on
        which History RAM starts acquiring pattern information.

        If History RAM trigger is configured as HistoryRAMTriggerType.PATTERN_LABEL,
        pattern_label_history_ram_trigger_label should be used to specify the pattern label from
        which to start acquiring pattern information.
        pattern_label_history_ram_trigger_vector_offset should be used to specify the number of
        vectors following the specified pattern label from which to start acquiring pattern
        information.
        pattern_label_history_ram_trigger_cycle_offset should be used to specify the number of
        cycles following the specified pattern label and vector offset from which to start acquiring
        pattern information.

        For all History RAM trigger conditions, history_ram_pretrigger_samples should be used to
        specify the number of samples to acquire before the trigger conditions are met. If you
        configure History RAM to only
        acquire failed cycles, you must set history_ram_pretrigger_samples to 0.

        history_ram_cycles_to_acquire should be used to specify which cycles History RAM acquires
        after the trigger conditions are met.

        Returns:
            per_site_cycle_information (list of HistoryRAMCycleInformation): Returns a list of
            class instances with the following information about each pattern cycle:
                -  **pattern_name** (str)  Name of the pattern for the acquired cycle.
                -  **time_set_name** (str) Time set for the acquired cycle.
                -  **vector_number** (int) Vector number within the pattern for the acquired cycle.
                    Vector numbers start
                   at 0 from the beginning of the pattern.
                -  **cycle_number** (int) Cycle number acquired by this History RAM sample. Cycle
                    numbers start at 0
                   from the beginning of the pattern burst.
                -  **scan_cycle_number** (int) Scan cycle number acquired by this History RAM
                    sample. Scan cycle numbers. start at 0 from the first cycle of the scan vector.
                    Scan cycle numbers are -1 for cycles that do not have a scan opcode.
                -  **expected_pin_states** (list of lists of enums.PinState) Pin states as expected
                    by the loaded pattern in the order specified in the pin list. Pins without
                    defined edges in the specified DUT cycle will have a value of
                    PinState.PIN_STATE_NOT_ACQUIRED. Length of the outer list will be equal to the
                    value of edge multiplier for the given vector. Length of the inner list will be
                    equal to the number of pins requested.
                -  **actual_pin_states** (list of lists of enums.PinState) Pin states acquired by
                    History RAM in the order specified in the pin list. Pins without defined edges
                    in the specified DUT cycle will have a value of PinState.PIN_STATE_NOT_ACQUIRED.
                   Length of the outer list will be equal to the value of edge multiplier for the
                   given vector. Length of the inner list will be equal to the number of pins
                   requested.
                -  **per_pin_pass_fail** (list of lists of bool) Pass fail information for pins in
                    the order specified in the pin list. Pins without defined edges in the specified
                    DUT cycle will have a value of pass (True). Length of the outer list will be
                    equal to the value of edge multiplier for the given vector. Length of the inner
                    list will be equal to the number of pins requested.
        """
        (
            per_instrument_per_site_cycle_information,
            number_of_samples,
        ) = self.ssc.stream_hram_results()
        per_instrument_per_site_to_per_site_lut = (
            self.ssc.calculate_per_instrument_per_site_to_per_site_lut(self.sites)
        )
        per_site_cycle_information = [
            [HistoryRAMCycleInformation(0, 0, 0, 0, 0, 0, 0, 0)] * number_of_samples
            for _ in self.sites
        ]
        for lut, cycle_information in zip(
            per_instrument_per_site_to_per_site_lut,
            per_instrument_per_site_cycle_information,
        ):
            for index in lut.location_1d_array:
                per_site_cycle_information[index] = cycle_information
        return per_site_cycle_information

    def burst_pattern_pass_fail(
        self,
        start_label: str,
        select_digital_function: bool = True,
        timeout: float = 10,
    ):
        """
        Uses the start_label you specify to burst the pattern on the sites you specify. Waits for
        the burst to complete, and returns comparison results for each site.Digital pins retain
        their state at the end of a pattern burst until the first vector of the pattern burst, a
        call to write_static, or a call to apply_levels_and_timing.

        Args:
            start_label (str): Pattern name or exported pattern label from which to start bursting
                the pattern.

            select_digital_function (bool, optional): A Boolean that specifies whether to select the
                digital method for the pins in the pattern prior to bursting. Defaults to True.

            timeout (float in seconds, optional): Maximum time (in seconds) allowed for this method
                to complete. If this method does not complete within this time interval, this method
                returns an error.Defaults to 10.

        Returns:
            List of pass_fail ({ int: bool, int: bool, ... }): Dictionary where each key is a site
                number and value is pass/fail.
        """
        initialized_array = [False for _ in self.sites]
        per_instrument_to_per_site_lut = self.ssc.calculate_per_instrument_to_per_site_lut(
            self.sites
        )
        per_instrument_pass = self.ssc.burst_pattern_pass_fail(
            start_label, select_digital_function, timeout
        )
        per_site_pass = _apply_lut_per_instrument_to_per_site(
            initialized_array, per_instrument_to_per_site_lut, per_instrument_pass
        )
        return per_site_pass

    def get_fail_count(self):
        """
        Returns the comparison fail count for pins in the repeated capabilities.

        Returns:
            failure_count (list of lists of int): Number of failures per site per pin. If a site is
            disabled or not enabled for burst, the method does not return data for that site. You
            can also use the get_pin_results_pin_information method to obtain a sorted list of
            returned sites and channels.
        """
        initialized_array = [[0 for _ in self.pins] for _ in self.sites]
        per_instrument_to_per_site_per_pin_lut = (
            self.ssc.calculate_per_instrument_to_per_site_per_pin_lut(self.sites, self.pins)
        )
        per_instrument_failure_counts = self.ssc.get_fail_count()
        per_site_per_pin_fail_counts = _apply_lut_per_instrument_to_per_site_per_pin(
            initialized_array,
            per_instrument_to_per_site_per_pin_lut,
            per_instrument_failure_counts,
        )
        return per_site_per_pin_fail_counts

    def get_site_pass_fail(self):
        """
        Returns value as list of pass/fail for each pin in the current context

        Returns:
            pass_fail (List[Bool]): list of pass or fail for each pin
        """
        initialized_array = [False for _ in self.sites]
        per_instrument_to_per_site_lut = self.ssc.calculate_per_instrument_to_per_site_lut(
            self.sites
        )
        per_instrument_pass = self.ssc.get_site_pass_fail()
        per_site_pass = _apply_lut_per_instrument_to_per_site(
            initialized_array, per_instrument_to_per_site_lut, per_instrument_pass
        )
        return per_site_pass

    def apply_tdr_offsets_per_site_per_pin(
        self, per_site_per_pin_tdr_values: typing.List[typing.List[float]]
    ):
        """
        Applies the correction for propagation delay offsets to a digital pattern instrument. Use
        this method to apply TDR offsets that are stored from a past measurement or are measured by
        means other than the tdr method. Also use this method to apply correction for offsets if the
        **applyOffsets** input of the tdr method was set to False at the time of measurement.

        Args:
            per_site_per_pin_tdr_values (typing.List[typing.List[float]]): TDR offsets to apply, in
            seconds. Specify an offset for each pin or channel.
        """
        (
            per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_per_pin_to_per_instrument_lut(self.sites, self.pins)
        initialized_array = [
            [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_tdr_values = _apply_lut_per_site_per_pin_to_per_instrument(
            initialized_array,
            per_site_per_pin_to_per_instrument_lut,
            per_site_per_pin_tdr_values,
        )
        self.ssc.apply_tdr_offsets(per_instrument_tdr_values)

    def configure_single_level_per_site(
        self,
        level_type_to_set: LevelTypeToSet,
        per_site_value: typing.List[float],
    ):
        """
        LevelTypeToSet
            VIH or VIL - Specifies the voltage that the digital pattern instrument will apply to the
                input of the DUT when the test instrument drives a logic high (1) or low (0).
            VOH or VOL - Specifies the output voltage from the DUT above (or below) which the
                comparator on the digital pattern test instrument interprets a logic high (H) or
                low (L).
            VTERM - Specifies the termination voltage the digital pattern instrument applies during
                non-drive cycles when the termination mode is set to V :sub:`term`. The instrument
                applies the termination voltage through a 50 Ω parallel termination resistance.
            IOL or IOH - Specifies the current that the DUT sources (or sinks) to the active load
                while outputting a voltage above (or below) VCOM.
            VCOM - Specifies the voltage level at which the active load circuit switches between
                sourcing current and sinking current.

        Args:
            level_type_to_set (LevelTypeToSet): VIH or VIL or VOH or VOL or IOL or IOH or VCOM or
                VTERM
            per_site_value (typing.List[float]): values to set per site
        """
        (
            per_site_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_to_per_instrument_lut(self.sites)
        initialized_array = [
            [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_value = _apply_lut_per_site_to_per_instrument(
            initialized_array, per_site_to_per_instrument_lut, per_site_value
        )
        self.ssc.configure_single_level_per_site(level_type_to_set, per_instrument_value)

    def configure_time_set_compare_edge_per_site_per_pin(
        self,
        time_set: str,
        per_site_per_pin_compare_strobe: typing.List[typing.List[float]],
    ):
        """
        Configures the strobe edge time for the pins in the context. Use this method to modify time
        set values after applying a timing sheet with the apply_levels_and_timing method, or to
        create time sets programmatically without the use of timing sheets. This method does not
        modify the timing sheet file or the timing sheet contents that will be used in future calls
        to apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.
            per_site_per_pin_compare_strobe (typing.List[typing.List[float]]): Time when the
                comparison happens within a vector period.
        """
        (
            per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_per_pin_to_per_instrument_lut(self.sites, self.pins)
        initialized_array = [
            [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_compare_strobe = _apply_lut_per_site_per_pin_to_per_instrument(
            initialized_array,
            per_site_per_pin_to_per_instrument_lut,
            per_site_per_pin_compare_strobe,
        )
        self.ssc.configure_time_set_compare_edge_per_site_per_pin(
            time_set, per_instrument_compare_strobe
        )

    def configure_time_set_compare_edge_per_site(
        self, time_set: str, per_site_compare_strobe: typing.List[float]
    ):
        """
        Configures the strobe edge time for the pins in context. Use this method to modify time set
        values after applying a timing sheet with the apply_levels_and_timing method, or to create
        time sets programmatically without the use of timing sheets. This method does not modify the
        timing sheet file or the timing sheet contents that will be used in future calls to
        apply_levels_and_timing; it only affects the values of the current timing context.

        Args:
            time_set (str): The specified time set name.

            per_site_compare_strobe (typing.List[float]): Time when the comparison happens within a
            vector period.
        """
        (
            per_site_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_to_per_instrument_lut(self.sites)
        initialized_array = [
            [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_compare_strobe = _apply_lut_per_site_to_per_instrument(
            initialized_array, per_site_to_per_instrument_lut, per_site_compare_strobe
        )
        self.ssc.configure_time_set_compare_edge_per_site(time_set, per_instrument_compare_strobe)

    def ppmu_measure_current(self):
        """
        Instructs the PPMU to measure current.

        Returns:
            per_site_per_pin_measurements (list of float): The returned array of measurements in the
            order you specify in the repeated capabilities. If a site is disabled, the method does
            not return data for that site. You can also use the get_pin_results_pin_information
            method to obtain a sorted list of returned sites and channels.
        """
        initialized_array = [[0.0 for _ in self.pins] for _ in self.sites]
        per_instrument_to_per_site_per_pin_lut = (
            self.ssc.calculate_per_instrument_to_per_site_per_pin_lut(self.sites, self.pins)
        )
        per_instrument_measurements = self.ssc.ppmu_measure(enums.PPMUMeasurementType.CURRENT)
        per_site_per_pin_measurements = _apply_lut_per_instrument_to_per_site_per_pin(
            initialized_array,
            per_instrument_to_per_site_per_pin_lut,
            per_instrument_measurements,
        )
        return per_site_per_pin_measurements

    def ppmu_measure_voltage(self):
        """
        Instructs the PPMU to measure voltage. This method can be called to take a voltage
        measurement even if the pin method is not set to PPMU.

        Returns:
            per_site_per_pin_measurements (list of float): The returned array of measurements in the
            order you specify in the repeated capabilities. If a site is disabled, the method does
            not return data for that site. You can also use the get_pin_results_pin_information
            method to obtain a sorted list of returned sites and channels.
        """
        initialized_array = [[0.0 for _ in self.pins] for _ in self.sites]
        per_instrument_to_per_site_per_pin_lut = (
            self.ssc.calculate_per_instrument_to_per_site_per_pin_lut(self.sites, self.pins)
        )
        per_instrument_measurements = self.ssc.ppmu_measure(enums.PPMUMeasurementType.VOLTAGE)
        per_site_per_pin_measurements = _apply_lut_per_instrument_to_per_site_per_pin(
            initialized_array,
            per_instrument_to_per_site_per_pin_lut,
            per_instrument_measurements,
        )
        return per_site_per_pin_measurements

    def ppmu_source_voltage_per_site_per_pin(
        self,
        current_limit_range: float,
        per_site_per_pin_source_voltages: typing.List[typing.List[float]],
    ):
        """
        Configures the PPMU to output function as Voltage and starts sourcing voltage from the PPMU.
        configures the current limit range for sourcing voltage.

        Args:
            current_limit_range (float): common current limit for all session channels
            per_site_per_pin_source_voltages (typing.List[typing.List[float]]): list of source
            voltage for each site for each pin
        """
        (
            per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_per_pin_to_per_instrument_lut(self.sites, self.pins)
        initialized_array = [
            [0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_source_voltages = _apply_lut_per_site_per_pin_to_per_instrument(
            initialized_array,
            per_site_per_pin_to_per_instrument_lut,
            per_site_per_pin_source_voltages,
        )
        self.ssc.ppmu_source_voltage_per_site_per_pin(
            current_limit_range, per_instrument_source_voltages
        )

    def ppmu_source_voltage_per_site(
        self,
        current_limit_range: float,
        per_site_source_voltages: typing.List[float],
    ):
        """
        Configures the PPMU to output function as Voltage and starts sourcing voltage from the PPMU.
        configures the current limit range for sourcing voltage.

        Args:
            current_limit_range (float): common current limit for all session channels
            per_site_source_voltages (typing.List[typing.List[float]]): list of source voltage for
            each site
        """
        (
            per_site_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_to_per_instrument_lut(self.sites)
        initialized_array = [
            [0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_source_voltages = _apply_lut_per_site_to_per_instrument(
            initialized_array, per_site_to_per_instrument_lut, per_site_source_voltages
        )
        self.ssc.ppmu_source_voltage_per_site(current_limit_range, per_instrument_source_voltages)

    def fetch_capture_waveform(self, waveform_name: str, samples_to_read: int, timeout: float = 10):
        """
        Returns dictionary where each key is a site number and value is a collection of digital
        states representing capture waveform data

        Args:
            waveform_name (str): Waveform name you create with the create capture waveform method.
            Use the waveform_name parameter with capture_start opcode in your pattern.

            samples_to_read (int): Number of samples to fetch.

            timeout (float, optional): Maximum time (in seconds) allowed for this method to
            complete. If this method does not complete within this time interval, this method
            returns an error. Defaults to 10.

        Returns:
            per site waveform capture ({ int: memory view of array. array of unsigned int,
            int: memory view of array. array of unsigned int, ... }): Dictionary where each key is
            a site number and value is a collection of digital states representing capture waveform
            data
        """
        initialized_array = [[0 for _ in range(samples_to_read)] for _ in range(len(self.sites))]
        per_instrument_to_per_site_lut = self.ssc.calculate_per_instrument_to_per_site_lut(
            self.sites
        )
        per_instrument_capture = self.ssc.fetch_capture_waveform(
            waveform_name, samples_to_read, timeout
        )
        per_site_waveforms = _apply_lut_per_instrument_to_per_site(
            initialized_array, per_instrument_to_per_site_lut, per_instrument_capture
        )
        return per_site_waveforms

    def write_source_waveform_site_unique(
        self,
        waveform_name: str,
        per_site_waveforms: typing.List[typing.List[int]],
        expand_to_minimum_size: bool = False,
        minimum_size: int = 128,
    ):
        """
        Writes one waveform per site. Use this method if you set the parameter of the create source
        waveform method to Site Unique.

        Args:
            waveform_name (str): The name to assign to the waveform. Use the waveform_name with
            source_start opcode in your pattern.
            per_site_waveforms (typing.List[typing.List[int]]): list of waveform_data for each site
            ({ int: basic sequence of unsigned int, int: basic sequence of unsigned int, ... }):
            Dictionary where each key is a site number and value is a collection of samples to use
            as source data expand_to_minimum_size (bool, optional): if set to true the array of
            waveform will be of "minimum_size" parameter with zeros padded as required. Defaults to
            False.
            minimum_size (int, optional): specifies the minimum length of each waveform per site.
            Defaults to 128.

        """
        # checked _
        _, cols = numpy.shape(per_site_waveforms)
        (
            per_site_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_to_per_instrument_lut(self.sites)
        initialized_array = [
            [[0 for _ in range(cols)] for _ in range(max_sites_on_instrument)]
            for _ in range(instrument_count)
        ]
        per_instrument_waveforms = _apply_lut_per_site_to_per_instrument(
            initialized_array, per_site_to_per_instrument_lut, per_site_waveforms
        )
        self.ssc.write_source_waveform_site_unique(
            waveform_name,
            per_instrument_waveforms,
            expand_to_minimum_size,
            minimum_size,
        )

    def read_static(self, auto_select=True):
        """
        auto_select=True, specifies this function to configure the output function as digital
        automatically.auto_select=False, if the pin is explicitly configured as digital already
        with the tsm_object.ssc.select_function(). Without configuring as digital and auto_select
        as false, this function will not work as expected.
        """
        if auto_select:
            self.ssc.select_function(enums.SelectedFunction.DIGITAL)
        initialized_array = [[enums.PinState.ZERO for _ in self.pins] for _ in self.sites]
        per_instrument_to_per_site_per_pin_lut = (
            self.ssc.calculate_per_instrument_to_per_site_per_pin_lut(self.sites, self.pins)
        )
        per_instrument_data = self.ssc.read_static()
        per_site_per_pin_data = _apply_lut_per_instrument_to_per_site_per_pin(
            initialized_array, per_instrument_to_per_site_per_pin_lut, per_instrument_data
        )
        return per_site_per_pin_data

    def write_static_per_site_per_pin(
        self,
        per_site_per_pin_state: typing.List[typing.List[enums.WriteStaticPinState]],
        auto_select=True,
    ):
        """
        auto_select=True, specifies this function to configure the output function as digital
        automatically.auto_select=False, if the pin is explicitly configured as digital already
        with the tsm_object.ssc.select_function(). Without configuring as digital and auto_select
        as false, this function will not work as expected.
        """
        if auto_select:
            self.ssc.select_function(enums.SelectedFunction.DIGITAL)
        (
            per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_per_pin_to_per_instrument_lut(self.sites, self.pins)
        initialized_array = [
            [enums.WriteStaticPinState.ZERO for _ in range(max_sites_on_instrument)]
            for _ in range(instrument_count)
        ]
        per_instrument_state = _apply_lut_per_site_per_pin_to_per_instrument(
            initialized_array,
            per_site_per_pin_to_per_instrument_lut,
            per_site_per_pin_state,
        )
        self.ssc.write_static_per_site_per_pin(per_instrument_state)

    def write_static_per_site(
        self, per_site_state: typing.List[enums.WriteStaticPinState], auto_select=True
    ):
        """
        auto_select=True, specifies this function to configure the output function as digital
        automatically. auto_select=False, if the pin is explicitly configured as digital already
        with the tsm_object.ssc.select_function(). Without configuring as digital and auto_select
        as false, this function will not work as expected.
        """
        if auto_select:
            self.ssc.select_function(enums.SelectedFunction.DIGITAL)
        (
            per_site_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = self.ssc.calculate_per_site_to_per_instrument_lut(self.sites)
        initialized_array = [
            [enums.WriteStaticPinState.X for _ in range(max_sites_on_instrument)]
            for _ in range(instrument_count)
        ]
        per_instrument_state = _apply_lut_per_site_to_per_instrument(
            initialized_array, per_site_to_per_instrument_lut, per_site_state
        )
        self.ssc.write_static_per_site(per_instrument_state)

    def publish(self, data_to_publish: typing.List[typing.Any], published_data_id: str = ""):
        """
        To publish the data to tsm context so that the same is available in teststand for data
        validation

        Args:
            data_to_publish (typing.List[typing.Any]): list of results or list of lists containing
            results. Other formats are not supported
            published_data_id (str, optional): a unique variable with which the data is available
            to in the tsm context for fetching it from teststand. Defaults to "".

        Raises:
            TypeError: when there is mismatch in datatype, it raises this exception.
        """
        if len(numpy.shape(data_to_publish)) == 1:
            (
                per_site_to_per_instrument_lut,
                instrument_count,
                max_sites_on_instrument,
            ) = self.ssc.calculate_per_site_to_per_instrument_lut(self.sites)
            default = {bool: False, float: 0.0}[type(data_to_publish[0])]
            initialized_array = [
                [default for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
            ]
            per_instrument_data = _apply_lut_per_site_to_per_instrument(
                initialized_array, per_site_to_per_instrument_lut, data_to_publish
            )
            self.pin_query_context.publish(per_instrument_data, published_data_id)
        elif len(numpy.shape(data_to_publish)) == 2:
            (
                per_site_per_pin_to_per_instrument_lut,
                instrument_count,
                max_sites_on_instrument,
            ) = self.ssc.calculate_per_site_per_pin_to_per_instrument_lut(self.sites, self.pins)
            default = {bool: False, float: 0.0}[type(data_to_publish[0][0])]
            initialized_array = [
                [default for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
            ]
            per_instrument_data = _apply_lut_per_site_per_pin_to_per_instrument(
                initialized_array, per_site_per_pin_to_per_instrument_lut, data_to_publish
            )
            self.pin_query_context.publish(per_instrument_data, published_data_id)
        else:
            raise TypeError("Unexpected data_to_publish array dimension.")


def filter_sites(tsm: TSMDigital, desired_sites: typing.List[int]):
    """
    filter  the sites specified in the current TSMObject

    Args:
        tsm (TSMDigital): tsm object from which sites to filter
        desired_sites (typing.List[int]): sites

    Returns:
        tsm (TSMDigital): tsm object with filtered sites
    """
    ssc = tsm.ssc.filter_sites(desired_sites)
    return TSMDigital(tsm.pin_query_context, ssc, desired_sites, tsm.pins)


def _apply_lut_per_instrument_to_per_site_per_pin(
    initialized_array: typing.List[typing.List[typing.Any]],
    lut: typing.List[Location2DArray],
    results_to_apply_lut_to: typing.List[typing.List[typing.Any]],
):
    """
    private function to convert the data to the required table lists

    Args:
        initialized_array (typing.List[typing.List[typing.Any]]): List containing the result
            information
        lut (typing.List[Location2DArray]): Lookup table containing the location information
        results_to_apply_lut_to (typing.List[typing.List[typing.Any]]): result array

    Returns:
        array_out: converted list of data
    """
    array_out = copy.deepcopy(initialized_array)
    for _lut, _results_to_apply_lut_to in zip(lut, results_to_apply_lut_to):
        for location, result in zip(_lut.location_2d_array, _results_to_apply_lut_to):
            array_out[location.row][location.col] = result
    return array_out


def _apply_lut_per_instrument_to_per_site(
    initialized_array: typing.List[typing.Any],
    lut: typing.List[Location1DArray],
    results_to_apply_lut_to: typing.List[typing.List[typing.Any]],
):
    """
    private function to convert the data to the required table lists

    Args:
        initialized_array (typing.List[typing.Any]): List containing the result information
        lut (typing.List[Location1DArray]): Lookup table containing the location information
        results_to_apply_lut_to (typing.List[typing.List[typing.Any]]): result array

    Returns:
        array_out: converted list of data
    """
    array_out = copy.deepcopy(initialized_array)
    for _lut, _results_to_apply_lut_to in zip(lut, results_to_apply_lut_to):
        for index, result in zip(_lut.location_1d_array, _results_to_apply_lut_to):
            array_out[index] = result
    return array_out


def _apply_lut_per_site_per_pin_to_per_instrument(
    initialized_array: typing.List[typing.List[typing.Any]],
    lut: typing.List[typing.List[Location2D]],
    results_to_apply_lut_to: typing.List[typing.List[typing.Any]],
):
    """
    private function to convert the data to the required table lists

    Args:
        initialized_array (typing.List[typing.List[typing.Any]]): List containing the result
            information
        lut (typing.List[typing.List[Location2D]]): Lookup table containing the location
            information
        results_to_apply_lut_to (typing.List[typing.List[typing.Any]]): result array

    Returns:
        array_out: converted list of data
    """
    array_out = copy.deepcopy(initialized_array)
    for _lut, _results_to_apply_lut_to in zip(lut, results_to_apply_lut_to):
        for location, result in zip(_lut, _results_to_apply_lut_to):
            array_out[location.row][location.col] = result
    return array_out


def _apply_lut_per_site_to_per_instrument(
    initialized_array: typing.List[typing.List[typing.Any]],
    lut: typing.List[Location2D],
    results_to_apply_lut_to: typing.List[typing.Any],
):
    """
    private function to convert the data to the required table lists

    Args:
        initialized_array (typing.List[typing.List[typing.Any]]): List containing the result
        information
        lut (typing.List[Location2D]): Lookup table containing the location information
        results_to_apply_lut_to (typing.List[typing.Any]): result array

    Returns:
        array_out: converted list of data
    """
    array_out = copy.deepcopy(initialized_array)
    for location, result in zip(lut, results_to_apply_lut_to):
        array_out[location.row][location.col] = result
    return array_out


def _arrange_channels_per_site(channel_list_string: str, site_list_string: str):
    """
    private function for converting channel list string and site list string to list of channels,
    sites and site numbers

    Args:
        channel_list_string (str): comma separated string of channel list
        site_list_string (str): comma separated string of site list

    Returns:
        channel_list_array, site_list_array, site_numbers: tuple of list of channels, sites string
        and site numbers
    """
    site_numbers, site_list_array = _site_list_to_site_numbers(site_list_string)
    channels, _, sites = _channel_list_to_pins(channel_list_string)
    channel_list_array: typing.List[str] = []
    for site_number in site_numbers:
        channel_list: typing.List[str] = []
        for channel, site in zip(channels, sites):
            if site_number == site:
                channel_list.append(channel)
        channel_list_array.append(",".join(channel_list))
    return channel_list_array, site_list_array, site_numbers


def _site_list_to_site_numbers(site_list: str):
    """
    private function to convert site list string to site numbers and site numbers strings

    Args:
        site_list (str): comma separated values of sites

    Returns:
        site_numbers, sites: numbers list of sites adn string list of sites
    """
    sites = re.split(r"\s*,\s*", site_list)
    site_numbers = [int(re.match(r"site(\d+)", site).group(1)) for site in sites]
    return site_numbers, sites


def _channel_list_to_pins(channel_list: str):
    """
    private function for converting the channel list into channels, pins and sites .

    Args:
        channel_list (str): comma separated list of channels

    Returns:
        channels, pins and sites: string list of channels, Pins and sites
    """
    channels = re.split(r"\s*,\s*", channel_list)
    sites = [-1] * len(channels)
    pins = channels[:]
    for i in range(len(channels)):
        try:
            site, pins[i] = re.split(r"[/\\]", channels[i])
        except ValueError:
            pass
        else:
            sites[i] = int(re.match(r"site(\d+)", site).group(1))
    return channels, pins, sites


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm: SMContext, options: dict = {}):
    """
    Creates the sessions for all the nidigital resource string available in the
    tsm context for instruments
    """
    pin_map_file_path = tsm.pin_map_file_path
    instrument_names = tsm.get_all_nidigital_instrument_names()
    if instrument_names:
        specifications_files = tsm.nidigital_project_specifications_file_paths
        levels_files = tsm.nidigital_project_levels_file_paths
        timing_files = tsm.nidigital_project_timing_file_paths
        pattern_files = tsm.nidigital_project_pattern_file_paths
        source_waveform_files = tsm.nidigital_project_source_waveform_file_paths
        capture_waveform_files = tsm.nidigital_project_capture_waveform_file_paths
        for instrument_name in instrument_names:
            session = nidigital.Session(instrument_name, options=options)
            tsm.set_nidigital_session(instrument_name, session)
            session.load_pin_map(pin_map_file_path)
            session.load_specifications_levels_and_timing(
                specifications_files, levels_files, timing_files
            )
            session.unload_all_patterns()
            for pattern_file in pattern_files:
                session.load_pattern(pattern_file)
            for capture_waveform_file in capture_waveform_files:
                filename = os.path.basename(capture_waveform_file)
                waveform_name, _ = filename.split(".")
                session.create_capture_waveform_from_file_digicapture(
                    waveform_name, capture_waveform_file
                )
            for source_waveform_file in source_waveform_files:
                filename = os.path.basename(source_waveform_file)
                waveform_name, _ = filename.split(".")
                session.create_source_waveform_from_file_tdms(
                    waveform_name, source_waveform_file, False
                )


@nitsm.codemoduleapi.code_module
def pins_to_sessions(
    tsm: SMContext,
    pins: typing.Union[str, typing.List[str]],
    sites: typing.List[int] = [],
    turn_pin_groups_to_pins: bool = True,
):
    """
    Get the sessions for the given Pins and return the pin query object for operating on the Pins.

    Args:
        tsm (SMContext): tsm context for nidigital.
        pins typing.Union[str, typing.List[str]]: desired pins for which the TSMDigital object is
            created. single pin name in string data type. List of strings for multiple pins.
        sites (typing.List[int], optional): list of desired sites. Defaults to [].
        turn_pin_groups_to_pins (bool, optional): converts all the Pin groups into pins.
            Defaults to True.

    Returns:
        digital_tsm: pin-query context variable
    """
    if isinstance(pins, str):
        pins = [pins]
    if len(sites) == 0:
        sites = list(tsm.site_numbers)
    if turn_pin_groups_to_pins:
        pins = list(tsm.get_pins_in_pin_groups(pins))
    sscs: typing.List[_NIDigitalSSC] = []
    (pin_query_context, sessions, pin_set_strings) = tsm.pins_to_nidigital_sessions_for_ppmu(pins)
    _, _, site_lists = tsm.pins_to_nidigital_sessions_for_pattern(pins)
    for session, pin_set_string, site_list in zip(sessions, pin_set_strings, site_lists):
        sscs.append(_NIDigitalSSC(session, pin_set_string, site_list))
    nidigital_tsm = _NIDigitalTSM(sscs)
    return TSMDigital(pin_query_context, nidigital_tsm, sites, pins)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    """Closes the sessions associated with the tsm context"""
    sessions = tsm.get_all_nidigital_sessions()
    for session in sessions:
        session.reset()
        session.close()

# End of TSMContext #
