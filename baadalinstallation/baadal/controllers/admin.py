# -*- coding: utf-8 -*-
###################################################################################
# Added to enable code completion in IDE's.
if 0:
    from gluon import *  # @UnusedWildImport
    import gluon
    global db; db = gluon.sql.DAL()
    global request; request = gluon.globals.Request
    global session; session = gluon.globals.Session()
    import logger
    from admin_model import get_add_template_form, get_add_host_form
###################################################################################

def add_template():

    form = get_add_template_form()
    
    if form.accepts(request.vars, session):
        logger.debug('New Template Created')
        redirect(URL(c='default', f='index'))
    elif form.errors:
        logger.error('Error in form')
    return dict(form=form)


def host_details():

    hosts = db(db.host.id >= 0).select()
    results = []
    for host in hosts:
        results.append({'ip':host.host_ip, 'id':host.id, 'name':host.host_name, 'status':host.status})

    return dict(hosts=results)

def add_host():
    form = get_add_host_form()

    if form.accepts(request.vars, session):
        db(db.host.id == form.vars.id).update(status=HOST_STATUS_DOWN)  # @UndefinedVariable
        logger.debug('New Host Added')
        redirect(URL(c='default', f='index'))
    elif form.errors:
        logger.error('Error in form')
    return dict(form=form)
    