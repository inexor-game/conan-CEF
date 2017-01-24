from conans import ConanFile, CMake, tools, ConfigureEnvironment
import os
import shutil


class CEFConan(ConanFile):
    name = "CEF"
    version = "3.2704.1424.gc3f0a5b"
    url = "https://github.com/inexor-game/conan-CEF.git"
    license = "BSD-3Clause"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "use_sandbox": [True, False],
        "debug_info_flag_vs": ["-Zi", "-Z7"]
    }
    default_options = '''use_sandbox=False
    debug_info_flag_vs=-Z7'''
    generators = "cmake"
    exports = "CMakeLists.txt"

    def get_cef_distribution_name(self):
        platform = ""
        if self.settings.os == "Windows":
            platform = "windows"
        if self.settings.os == "Macos":
            platform = "macosx"
        if self.settings.os == "Linux":
            platform = "linux"
        if self.settings.arch == "x86":
            platform += "32"
        else:
            platform += "64"
        return "cef_binary_%s_%s" % (self.version, platform)

    def config(self):
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio" and self.settings.compiler.version != "14":
            self.options.remove("use_sandbox") # it requires to be built with that exact version for sandbox support

    def source(self):
        cef_download_filename ="{}.tar.bz2".format(self.get_cef_distribution_name())
        self.output.info("Downloading CEF prebuilts from opensource.spotify.com")
        tools.download("http://opensource.spotify.com/cefbuilds/{}".format(cef_download_filename), cef_download_filename)
        tools.unzip(cef_download_filename)
        os.unlink(cef_download_filename)
        cmake_vars_file = "{}/cmake/cef_variables.cmake".format(self.get_cef_distribution_name())
        if self.settings.compiler == "Visual Studio" and not (self.settings.compiler.runtime == "MT" or self.settings.compiler.runtime == "MTd"):
            tools.replace_in_file(cmake_vars_file, "/MT           # Multithreaded release runtime", "/MD           # Multithreaded release runtime")
            tools.replace_in_file(cmake_vars_file, "/MDd          # Multithreaded debug runtime", "/MDd          # Multithreaded debug runtime")
        tools.replace_in_file(cmake_vars_file, 'set(CEF_DEBUG_INFO_FLAG "/Zi"', 'set(CEF_DEBUG_INFO_FLAG "{}"'.format(self.options.debug_info_flag_vs))
        tools.replace_in_file(cmake_vars_file, 'set(CEF_DEBUG_INFO_FLAG "/Zi"', 'set(CEF_DEBUG_INFO_FLAG "{}"'.format(self.options.debug_info_flag_vs))
        

    def build(self):
        args = ["-DCEF_ROOT={}".format(self.get_cef_distribution_name())]
        args += ["-DUSE_SANDBOX={}".format("ON" if self.options.use_sandbox else "OFF")]

        cmake = CMake(self.settings)
        self.run('cmake {} {} {}'.format(self.conanfile_directory, cmake.command_line, " ".join(args)))
        self.run("cmake --build . {}".format(cmake.build_config))

    def package(self):
        # Copy headers
        self.copy('*', dst='include/include', src='{}/include'.format(self.get_cef_distribution_name()))

        # Copy all stuff from the Debug/Release folders in the downloaded cef bundle:
        dis_folder = "{}/{}".format(self.get_cef_distribution_name(), self.settings.build_type)
        res_folder = "{}/Resources".format(self.get_cef_distribution_name())
        # resource files: taken from cmake/cef_variables (on macosx we would need to convert the COPY_MACOSX_RESOURCES() function)
        cef_resources = ["cef.pak", "cef_100_percent.pak", "cef_200_percent.pak", "cef_extensions.pak", "devtools_resources.pak", "icudtl.dat", "locales*"]
        for res in cef_resources:
            self.copy(res, dst="bin", src=res_folder, keep_path=True)

        if self.settings.os == "Linux":
            # CEF binaries: (Taken from cmake/cef_variables)
            self.copy("libcef.so", dst="lib", src=dis_folder, keep_path=False)
            self.copy("natives_blob.bin", dst="bin", src=dis_folder, keep_path=False)
            self.copy("snapshot_blob.bin", dst="bin", src=dis_folder, keep_path=False)
            if self.options.use_sandbox:
                self.copy("chrome-sandbox", dst="bin", src=dis_folder, keep_path=False)
            self.copy("*cef_dll_wrapper.a", dst="lib", keep_path=False)
        if self.settings.os == "Windows":
            # CEF binaries: (Taken from cmake/cef_variables)
            self.copy("*.dll", dst="bin", src=dis_folder, keep_path=False)
            self.copy("libcef.lib", dst="lib", src=dis_folder, keep_path=False)
            self.copy("natives_blob.bin", dst="bin", src=dis_folder, keep_path=False)
            self.copy("snapshot_blob.bin", dst="bin", src=dis_folder, keep_path=False)
            if self.options.use_sandbox:
                self.copy("cef_sandbox.lib", dst="lib", src=dis_folder, keep_path=False)
            self.copy("*cef_dll_wrapper.lib", dst="lib", keep_path=False) # libcef_dll_wrapper is somewhere else

    def package_info(self):
        if self.settings.compiler == "Visual Studio":
            self.cpp_info.libs = ["libcef_dll_wrapper", "libcef"]
        else:
            self.cpp_info.libs = ["cef_dll_wrapper", "cef"]
            self.cpp_info.defines += ["_FILE_OFFSET_BITS=64"]
        
        if self.options.use_sandbox:
            if self.settings.os == "Windows":
                self.cpp_info.libs += ["cef_sandbox", "dbghelp", "psapi", "version", "winmm"]
            self.cpp_info.defines += ["USE_SANDBOX", "CEF_USE_SANDBOX", "PSAPI_VERSION=1"]
        if self.settings.os == "Windows":
            self.cpp_info.libs += ["glu32", "opengl32", "comctl32", "rpcrt4", "shlwapi", "ws2_32"]