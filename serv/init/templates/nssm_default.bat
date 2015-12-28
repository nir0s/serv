@echo off

echo Installing {{ name }} as a windows service...

"{{ nssm_dir }}\nssm.exe" install "{{ name }}" "{{ cmd }}" "{{ args }}"

if %errorlevel% neq 0 exit /b %errorlevel%

echo Setting service environment
{% if env %}{{ nssm_dir }}\nssm.exe set {{ name }} AppEnvironmentExtra ^
{% for var, value in env.items() %}{% filter upper %}{{ var }}{% endfilter %}={{ value }} ^
{% endfor %}EXAMPLE_ENVIRONMENT_VARIABLE=example_value{% endif %}

if %errorlevel% neq 0 exit /b %errorlevel%

echo Configuring startup policy...

sc config {{ name }} start= {{ startup_policy }}

if %errorlevel% neq 0 exit /b %errorlevel%

echo Configuring failure policy...

sc failure {{ name }} reset= {{ failure_reset_timeout }} actions= restart/{{ failure_restart_delay }}

if %errorlevel% neq 0 exit /b %errorlevel%

echo {{ name }} configured successfully as a Windows Service
