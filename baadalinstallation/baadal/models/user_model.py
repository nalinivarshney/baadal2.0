def get_vm_list(vm_data): 
    vmlist=[]
    for vm in vm_data:
        print vm.id
        total_cost = addtocost(vm.vm_name)
        element = {'name':vm.vm_name,'ip':vm.vm_ip, 'owner':vm.user_id, 'ip':vm.vm_ip, 'hostip':'hostip','RAM':vm.RAM,'vcpus':vm.vCPU,'level':vm.current_run_level,'cost':total_cost}
        vmlist.append(element)

    return vmlist

def get_my_vm_list():
    vms = db((db.vm_data.status != VM_STATUS_REQUESTED)and(db.vm_data.status != VM_STATUS_APPROVED)and(db.vm_data.user_id==auth.user.id)).select()
    return get_vm_list(vms)
