import SCons.SConf
import hashlib
import os
import os.path
import re

try:
    from shlex import quote
except:
    from pipes import quote

def _run_prog(context, src, suffix):
    # Workaround for a SCons bug.
    # RunProg uses a global incrementing counter for temporary .c file names. The
    # file name depends on the number of invocations of that function, but not on
    # the file contents. When the user subsequently invokes scons with different
    # options, the sequence of file contents passed to RunProg may vary. However,
    # RunProg may incorrectly use cached results from a previous run saved for
    # different file contents but the same invocation number. To prevent this, we
    # monkey patch its global counter with a hashsum of the file contents.
    # The workaround is needed only for older versions of SCons, where
    # _ac_build_counter was an integer.
    try:
        if type(SCons.SConf._ac_build_counter) is int:
            SCons.SConf._ac_build_counter = int(hashlib.md5(src.encode()).hexdigest(), 16)
    except:
        pass
    return context.RunProg(src, suffix)

def _get_llvm_dir(version):
    def macos_dirs():
        return [
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin',
        '/Library/Developer/CommandLineTools/usr/bin',
        ]

    def linux_dirs():
        suffixes = []
        for n in [3, 2, 1]:
            v = '.'.join(map(str, version[:n]))
            suffixes += [
                '-' + v,
                '/' + v,
            ]
        suffixes += ['']
        ret = []
        for s in suffixes:
            ret.append('/usr/lib/llvm%s/bin' % s)
        return ret

    for llvmdir in macos_dirs() + linux_dirs():
        if os.path.isdir(llvmdir):
            return llvmdir

def CheckLibWithHeaderExt(context, libs, headers, language, expr='1', run=True):
    if not isinstance(headers, list):
        headers = [headers]

    if not isinstance(libs, list):
        libs = [libs]

    name = libs[0]
    libs = [l for l in libs if not l in context.env['LIBS']]

    suffix = '.%s' % language.lower()
    includes = '\n'.join(['#include <%s>' % h for h in ['stdio.h'] + headers])
    src = """
%s

int main() {
    printf("%%d\\n", (int)(%s));
    return 0;
}
""" % (includes, expr)

    context.Message("Checking for %s library %s... " % (
        language.upper(), name))

    if run:
        err, out = _run_prog(context, src, suffix)
        if out.strip() == '0':
            err = True
    else:
        err = context.CompileProg(src, suffix)

    if not err:
        context.Result('yes')
        context.env.Append(LIBS=libs)
        return True
    else:
        context.Result('no')
        return False

def CheckProg(context, prog):
    context.Message("Checking for executable %s... " % prog)

    path = context.env.Which(prog)
    if path:
        context.Result(path[0])
        return True
    else:
        context.Result('not found')
        return False

def CheckCanRunProgs(context):
    context.Message("Checking whether we can run compiled executables... ")

    src = """
int main() {
    return 0;
}
"""

    err, out = _run_prog(context, src, '.c')

    if not err:
        context.Result('yes')
        return True
    else:
        context.Result('no')
        return False

def CheckCompilerOptionSupported(context, opt, language):
    context.Message("Checking whether %s compiler supports %s... " % (language.upper(), opt))

    ext = '.%s' % language.lower()
    src = "int main() { return 0; }"

    orig_env = context.env

    context.env = orig_env.Clone()
    context.env.Append(**{language.upper()+'FLAGS': [opt]})

    err = context.CompileProg(src, ext)

    context.env = orig_env

    if not err:
        context.Result('yes')
        return True
    else:
        context.Result('no')
        return False

def FindTool(context, var, toolchains, commands, prepend_path=[], required=True):
    env = context.env

    context.Message("Searching %s executable... " % var)

    if env.HasArgument(var):
        context.Result(env[var])
        return True

    toolchains = list(toolchains)

    for tc in list(toolchains):
        if '-pc-' in tc:
            toolchains += [tc.replace('-pc-', '-')]

        if 'android' in tc:
            m = re.search('((android(eabi)?)\d+)$', tc)
            if m:
                tc = tc.replace(m.group(1), m.group(2))
                toolchains += [tc]
            toolchains += [tc.replace('armv7a', 'arm')]

    if '' in toolchains:
        toolchains.remove('')
        toolchains.append('')

    found = False

    for tool_prefix in toolchains:
        for tool_cmd, tool_ver in commands:
            if isinstance(tool_cmd, list):
                tool_name = tool_cmd[0]
                tool_flags = tool_cmd[1:]
            else:
                tool_name = tool_cmd
                tool_flags = []

            if not tool_prefix:
                tool = tool_name
            else:
                tool = '%s-%s' % (tool_prefix, tool_name)

            if tool_ver:
                search_versions = [
                    tool_ver[:3],
                    tool_ver[:2],
                    tool_ver[:1],
                ]

                default_ver = env.ParseCompilerVersion(tool)

                if default_ver and default_ver[:len(tool_ver)] == tool_ver:
                    search_versions += [default_ver]

                for ver in reversed(sorted(set(search_versions))):
                    versioned_tool = '%s-%s' % (tool, '.'.join(map(str, ver)))
                    if env.Which(versioned_tool, prepend_path):
                        tool = versioned_tool
                        break

            tool_path = env.Which(tool, prepend_path)
            if not tool_path:
                continue

            if tool_ver:
                actual_ver = env.ParseCompilerVersion(tool_path[0])
                if actual_ver:
                    actual_ver = actual_ver[:len(tool_ver)]

                if actual_ver != tool_ver:
                    env.Die(
                        ("problem detecting %s: "+
                        "found '%s', which reports version %s, but expected version %s") % (
                            var,
                            tool_path[0],
                            '.'.join(map(str, actual_ver)) if actual_ver else '<unknown>',
                            '.'.join(map(str, tool_ver))))

            env[var] = tool_path[0]
            if tool_flags:
                env['%sFLAGS' % var] = ' '.join(tool_flags)

            found = True
            break

        if found:
            break

    if not found:
        if required:
            env.Die("can't find %s executable" % var)
        else:
            env[var] = None
            context.Result('not found')
            return False

    message = env[var]
    realpath = os.path.realpath(env[var])
    if realpath != env[var]:
        message += ' (%s)' % realpath

    context.Result(message)
    return True

def FindClangFormat(context):
    env = context.env

    context.Message("Searching for clang-format... ")

    if env.HasArgument('CLANG_FORMAT'):
        context.Result(env['CLANG_FORMAT'])
        return True

    min_ver = 10
    max_ver = 99

    def checkver(exe):
        ver_str = env.ParseToolVersion('%s --version' % exe)
        try:
            ver = tuple(map(int, ver_str.split('.')))
            return (min_ver, 0, 0) <= ver <= (max_ver, 99, 99)
        except:
            return False

    clang_format = env.Which('clang-format')
    if clang_format and checkver(clang_format[0]):
        env['CLANG_FORMAT'] = clang_format[0]
        context.Result(env['CLANG_FORMAT'])
        return True

    for ver in range(min_ver,max_ver+1):
        clang_format = env.Which('clang-format-%d' % ver)
        if clang_format and checkver(clang_format[0]):
            env['CLANG_FORMAT'] = clang_format[0]
            context.Result(env['CLANG_FORMAT'])
            return True

        llvmdir = _get_llvm_dir((ver,))
        if llvmdir:
            clang_format = os.path.join(llvmdir, 'clang-format')
            if checkver(clang_format):
                env['CLANG_FORMAT'] = clang_format
                context.Result(env['CLANG_FORMAT'])
                return True

    env.Die("can't find clang-format >= %s and <= %s" % (min_ver, max_ver))

def FindLLVMDir(context, version):
    context.Message(
        "Searching PATH for llvm %s... " % '.'.join(map(str, version)))

    llvmdir = _get_llvm_dir(version)
    if llvmdir:
        context.env['ENV']['PATH'] += ':' + llvmdir
        context.Result(llvmdir)
        return True

    context.Result('not found')
    return True

def FindLibDir(context, prefix, host):
    context.Message("Searching for system library directory... ")

    def _libdirs(host):
        dirs = ['lib/' + host]
        if 'x86_64-pc-linux-gnu' == host:
            dirs += ['lib/x86_64-linux-gnu']
        if 'x86_64' in host:
            dirs += ['lib64']
        dirs += ['lib']
        return dirs

    for d in _libdirs(host):
        libdir = os.path.join(prefix, d)
        if os.path.isdir(libdir):
            break

    context.env['ROC_SYSTEM_LIBDIR'] = libdir
    context.Result(libdir)
    return True

def FindConfigGuess(context):
    context.Message('Searching CONFIG_GUESS script... ')

    if context.env.HasArgument('CONFIG_GUESS'):
        context.Result(context.env['CONFIG_GUESS'])
        return True

    prefixes = [
        '/usr',
        '/usr/local',
        '/usr/local/Cellar',
    ]

    dirs = [
        'share/gnuconfig',
        'share/misc',
        'share/automake-*',
        'automake/*/share/automake-*',
        'share/libtool/build-aux',
        'libtool/*/share/libtool/build-aux',
        'lib/php/build',
        'lib/php/*/build',
    ]

    for p in prefixes:
        for d in dirs:
            for f in context.env.Glob(os.path.join(p, d, 'config.guess')):
                path = str(f)
                if not os.access(path, os.X_OK):
                    continue

                context.env['CONFIG_GUESS'] = path
                context.Result(path)

                return True

    context.Result('not found')
    return False

def FindPkgConfig(context, toolchain):
    env = context.env

    context.Message('Searching PKG_CONFIG... ')

    if env.HasArgument('PKG_CONFIG'):
        context.Result(env['PKG_CONFIG'])
        return True

    # https://autotools.io/pkgconfig/cross-compiling.html
    # http://tiny.cc/lh6upz
    if toolchain:
        if env.Which(toolchain + '-pkg-config'):
            env['PKG_CONFIG'] = toolchain + '-pkg-config'
            context.Result(env['PKG_CONFIG'])
            return True

        if 'PKG_CONFIG_PATH' in os.environ \
            or 'PKG_CONFIG_LIBDIR' in os.environ \
            or 'PKG_CONFIG_SYSROOT_DIR' in os.environ:
            if env.Which('pkg-config'):
                env['PKG_CONFIG'] = 'pkg-config'
                context.Result(env['PKG_CONFIG'])
                return True

        context.Result('not found')
        return False

    if env.Which('pkg-config'):
        env['PKG_CONFIG'] = 'pkg-config'
        context.Result(env['PKG_CONFIG'])
        return True

    context.Result('not found')
    return False

def FindPkgConfigPath(context, prefix):
    if not prefix.endswith(os.sep):
        prefix += os.sep

    env = context.env

    context.Message("Searching PKG_CONFIG_PATH...")

    if env.HasArgument('PKG_CONFIG_PATH'):
        context.Result(env['PKG_CONFIG_PATH'])
        return True

    # https://linux.die.net/man/1/pkg-config the default is libdir/pkgconfig
    env['PKG_CONFIG_PATH'] = os.path.join(env['ROC_SYSTEM_LIBDIR'], 'pkgconfig')

    pkg_config = env.get('PKG_CONFIG', None)
    if pkg_config:
        pkg_config_paths = env.GetCommandOutput(
            '%s --variable pc_path pkg-config' % quote(pkg_config))
        try:
            path_list = pkg_config_paths.split(':')
            def select_path():
                for path in path_list:
                    if path.startswith(prefix) and os.path.isdir(path):
                        return path
                for path in path_list:
                    if path.startswith(prefix):
                        return path

            path = select_path()
            if path:
                env['PKG_CONFIG_PATH'] = path
        except:
            pass

    context.Result(env['PKG_CONFIG_PATH'])
    return True

def AddPkgConfigDependency(context, package, flags):
    context.Message("Searching pkg-config package %s..." % package)

    env = context.env
    if 'PKG_CONFIG_DEPS' not in env.Dictionary():
        env['PKG_CONFIG_DEPS'] = []

    pkg_config = env.get('PKG_CONFIG', None)
    if not pkg_config:
        context.Result('pkg-config not available')
        return False

    cmd = '%s %s --silence-errors %s' % (quote(pkg_config), package, flags)
    try:
        if env.ParseConfig(cmd):
            env.AppendUnique(PKG_CONFIG_DEPS=[package])
            context.Result('yes')
            return True
    except:
        pass

    context.Result('not found')
    return False

def init(env):
    env.CustomTests = {
        'CheckLibWithHeaderExt': CheckLibWithHeaderExt,
        'CheckProg': CheckProg,
        'CheckCanRunProgs': CheckCanRunProgs,
        'CheckCompilerOptionSupported': CheckCompilerOptionSupported,
        'FindTool': FindTool,
        'FindClangFormat': FindClangFormat,
        'FindLLVMDir': FindLLVMDir,
        'FindLibDir': FindLibDir,
        'FindConfigGuess': FindConfigGuess,
        'FindPkgConfig': FindPkgConfig,
        'FindPkgConfigPath': FindPkgConfigPath,
        'AddPkgConfigDependency': AddPkgConfigDependency,
    }
