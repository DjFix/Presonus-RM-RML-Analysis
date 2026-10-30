#pragma once
#include <array>
#include <cstdint>

namespace presonus::uc {
struct FileTransferStateAccess;
}
namespace Presonus::UC {
struct FileRequestEvent;
class IFileRequestHandler;
class FileTransfer {
public:
  FileTransfer();
  ~FileTransfer();
  // Portable candidate factory spelling. Pointer return/static membership
  // are not established by the original mangled name; this method stays
  // declaration-pending even after its observed allocation/dataflow passes.
  static FileTransfer *create(const FileRequestEvent &, bool);

private:
  // Logical observed 32-bit values only, not original field names/types or
  // ARM layout. ARM +0x34 is unwritten by construction and is not modeled as
  // an initialized field here. Handler storage uses the native pointer type.
  std::array<std::uint32_t, 14> words;
  IFileRequestHandler *handler;
  friend struct presonus::uc::FileTransferStateAccess;
  // Source-port access; original source friendship is not established.
  friend class FileTransferManager;
};
} // namespace Presonus::UC
