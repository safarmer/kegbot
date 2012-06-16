#!/usr/bin/env python

import os
import shutil
import subprocess

COMPONENTS = [
    'https://bitbucket.org/wkornewald/djangoappengine',
    'https://bitbucket.org/wkornewald/djangotoolbox',
    'https://bitbucket.org/twanschik/django-autoload',
    'https://bitbucket.org/wkornewald/django-dbindexer',
]


def sh(command, capture=False, ignore_error=False, cwd=None):
    """Runs an external command. If capture is True, the output of the
    command will be captured and returned as a string.  If the command 
    has a non-zero return code raise a BuildFailure. You can pass
    ignore_error=True to allow non-zero return codes to be allowed to
    pass silently, silently into the night.  If you pass cwd='some/path'
    paver will chdir to 'some/path' before exectuting the command."""
    kwargs = { 'shell': True, 'cwd': cwd}
    if capture:
        kwargs['stderr'] = subprocess.STDOUT
        kwargs['stdout'] = subprocess.PIPE
    p = subprocess.Popen(command, **kwargs)
    p_stdout = p.communicate()[0]
    if p.returncode and not ignore_error:
        if capture:
            error(p_stdout)
        raise SystemError("Subprocess return code: %d" % p.returncode)

    if capture:
        return p_stdout

if __name__ == "__main__":
    for comp in COMPONENTS:
        name = comp.split('/')[-1]
        print("Cloning: %s" % name)
    
        if os.path.exists(name):
            print("  deleting old directory")
            shutil.rmtree(name)
        
        print("  clone started")
        sh("hg clone %s" % comp, capture=True)
        print("  clone complete")
        if name != "djangoappengine":
            print("  repackaging")
            pkg = name.split('-')[-1]
            
            if name != pkg:
                shutil.rmtree(pkg)
                shutil.move(os.path.join(name, pkg), pkg);
                print("  deleting old base directory")
                shutil.rmtree(name)
            else:
                shutil.move(os.path.join(name, pkg), "tmp");
                print("  deleting old base directory")
                shutil.rmtree(name)
                shutil.move("tmp", pkg);
                
    
