%global import() %%include %%(test -e %%{S:%%1} && echo %%{S:%%1} || echo %%{_sourcedir}/%%1)
%import source
