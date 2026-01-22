Error de servidor de Odoo

RPC_ERROR
Odoo Server Error

Occured on 201.132.21.90:9070 on model print.job on 2026-01-22 07:55:18 GMT

Traceback (most recent call last):
  File "/opt/odoo/odoo/odoo/http.py", line 2166, in _transactioning
    return service_model.retrying(func, env=self.env)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/service/model.py", line 156, in retrying
    result = func()
             ^^^^^^
  File "/opt/odoo/odoo/odoo/http.py", line 2133, in _serve_ir_http
    response = self.dispatcher.dispatch(rule.endpoint, args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/http.py", line 2381, in dispatch
    result = self.request.registry['ir.http']._dispatch(endpoint)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/addons/base/models/ir_http.py", line 333, in _dispatch
    result = endpoint(**request.params)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/http.py", line 754, in route_wrapper
    result = endpoint(self, *args, **params_ok)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/addons/web/controllers/dataset.py", line 42, in call_button
    action = call_kw(request.env[model], method, args, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/api.py", line 535, in call_kw
    result = getattr(recs, name)(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/extraaaddons/print-suite/print_finishing/models/print_job_inherit.py", line 212, in action_create_mo_with_wos
    bom = job._create_bom_for_job(product)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/extraaaddons/print-suite/print_finishing/models/print_job_inherit.py", line 157, in _create_bom_for_job
    self.env['mrp.bom.operation'].create({
    ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/api.py", line 614, in __getitem__
    return self.registry[model_name](self, (), ())
           ~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/opt/odoo/odoo/odoo/modules/registry.py", line 244, in __getitem__
    return self.models[model_name]
           ~~~~~~~~~~~^^^^^^^^^^^^
KeyError: 'mrp.bom.operation'

The above server error caused the following client error:
RPC_ERROR: Odoo Server Error
    RPC_ERROR
        at makeErrorFromResponse (http://201.132.21.90:9070/web/assets/6562353/web.assets_web.min.js:3165:165)
        at XMLHttpRequest.<anonymous> (http://201.132.21.90:9070/web/assets/6562353/web.assets_web.min.js:3170:13)
