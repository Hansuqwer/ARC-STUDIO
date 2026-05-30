import Foundation
import Virtualization

// Minimal source for the ARC VZ no-NIC proof helper.
// It intentionally configures zero network devices. The production proof path
// compiles this helper out-of-band and points ARC_VZ_RUNNER at the binary.

struct Args {
    let kernel: String
    let initrd: String
    let workspace: String
    let command: [String]
}

func parseArgs() -> Args? {
    var kernel = ""
    var initrd = ""
    var workspace = ""
    var command: [String] = []
    var i = 1
    let args = CommandLine.arguments
    while i < args.count {
        switch args[i] {
        case "--kernel": i += 1; if i < args.count { kernel = args[i] }
        case "--initrd": i += 1; if i < args.count { initrd = args[i] }
        case "--workspace": i += 1; if i < args.count { workspace = args[i] }
        case "--": command = Array(args[(i + 1)...]); i = args.count
        default: break
        }
        i += 1
    }
    if kernel.isEmpty || initrd.isEmpty || workspace.isEmpty { return nil }
    return Args(kernel: kernel, initrd: initrd, workspace: workspace, command: command)
}

guard let parsed = parseArgs() else {
    FileHandle.standardError.write(Data("usage: arc-vz-runner --kernel K --initrd I --workspace W -- cmd\n".utf8))
    exit(2)
}

let config = VZVirtualMachineConfiguration()
config.platform = VZGenericPlatformConfiguration()
let loader = VZLinuxBootLoader(kernelURL: URL(fileURLWithPath: parsed.kernel))
loader.initialRamdiskURL = URL(fileURLWithPath: parsed.initrd)
let encodedCommand = parsed.command
    .joined(separator: "\u{1f}")
    .data(using: .utf8)?
    .base64EncodedString() ?? ""
loader.commandLine = "console=hvc0 quiet ARC_VZ_COMMAND_B64=\(encodedCommand)"
config.bootLoader = loader
config.cpuCount = 1
config.memorySize = 512 * 1024 * 1024
config.networkDevices = []
config.entropyDevices = [VZVirtioEntropyDeviceConfiguration()]

let console = VZVirtioConsoleDeviceSerialPortConfiguration()
console.attachment = VZFileHandleSerialPortAttachment(fileHandleForReading: FileHandle.standardInput, fileHandleForWriting: FileHandle.standardOutput)
config.serialPorts = [console]

let share = VZSharedDirectory(url: URL(fileURLWithPath: parsed.workspace), readOnly: false)
let fs = VZVirtioFileSystemDeviceConfiguration(tag: "workspace")
fs.share = VZSingleDirectoryShare(directory: share)
config.directorySharingDevices = [fs]

do {
    try config.validate()
} catch {
    FileHandle.standardError.write(Data("VZ config invalid: \(error)\n".utf8))
    exit(1)
}

print("ARC_VZ_NETWORK_DEVICES=0")
print("ARC_VZ_NETWORK_DEVICES_CONFIGURED=0")
let vm = VZVirtualMachine(configuration: config)
vm.start { result in
    switch result {
    case .success:
        print("ARC_VZ_BOOTED=1")
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
            vm.stop { _ in exit(0) }
        }
    case .failure(let error):
        FileHandle.standardError.write(Data("VZ start failed: \(error)\n".utf8))
        exit(1)
    }
}
dispatchMain()
