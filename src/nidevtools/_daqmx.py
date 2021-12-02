import nidaqmx
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext

@nitsm.codemoduleapi.code_module
def clear_daqmx_task(tsm_context: SemiconductorModuleContext):
    tasks_ai = tsm_context.get_all_daqmx_task()#GETALLNIDAQmxTASK
    tasks_ao = tsm_context.get_all_daqmx_task()#GETALLNIDAQmxTASK
    for task_ai in tasks_ai:
        task_ai.stop()
        task_ai.close()
    for task_ao in tasks_ao:
        task_ao.stop()
        task_ao.close()
