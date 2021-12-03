import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext


@nitsm.codemoduleapi.code_module
def tsm_lear_daqmx_task(tsm_context: SemiconductorModuleContext):
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AI")
    tasks_ao = tsm_context.get_all_nidaqmx_tasks("AO")
    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ao:
        task.stop()
        task.close()


@nitsm.codemoduleapi.code_module
def tsm_set_daqmx_task(tsm_context: SemiconductorModuleContext):
    [task_names_ai, task_channels_ai] = tsm_context.get_all_nidaqmx_task_names("AI")
    [task_names_ao, task_channels_ao] = tsm_context.get_all_nidaqmx_task_names("AO")
    qty = min(len(task_names_ai), len(task_channels_ai))
    for task in range(qty):
        task_channel = task_channels_ai[qty]
        task_name = task_names_ai[qty]
        task = nidaqmx.Task()
        task.ai_channels.add_ai_voltage_chan(task_channel, task_name, TerminalConfiguration.DIFFERENTIAL, -10, 10)
        tsm_context.set_nidaqmx_task(task_name_ai, task)
    for task in range(qty):
        task_channel = task_channels_ao[qty]
        task_name = task_names_ao[qty]
        task = nidaqmx.Task()
        task.ai_channels.add_ai_voltage_chan(task_channel, task_name, TerminalConfiguration.RSE, -10, 10)
        tsm_context.set_nidaqmx_task(task_name_ao, task)
