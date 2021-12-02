import nidaqmx
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext

@nitsm.codemoduleapi.code_module
def clear_daqmx_task(tsm_context: SemiconductorModuleContext):
    tasks_AI = tsm_context.get_all_daqmx_task()#GETALLNIDAQmxTASK
    tasks_AO = tsm_context.get_all_daqmx_task()#GETALLNIDAQmxTASK
    for task_AI in tasks_AI:
        task_AI.stop()
        task_AI.close()
    for task_AO in tasks_AO:
        task_AO.stop()
        task_AO.close()
