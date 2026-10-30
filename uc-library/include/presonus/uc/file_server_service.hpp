#pragma once
#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/file_services.hpp"

namespace presonus::uc {
// Independent, mandatory service boundaries. These do not implement the
// original FileTransferManager/NetworkManager or establish their ABI.
class FileServerPorts {
public:
  virtual void acceptRequest(Presonus::UC::IFileRequestHandler &, int,
                             const Presonus::UC::FileRequestEvent &) = 0;
  virtual void sendDataEvent(const Presonus::UC::FileDataEvent &, int) = 0;

protected:
  ~FileServerPorts() = default;
};
} // namespace presonus::uc
namespace Presonus::UC {
// Original root-class RTTI and eight virtual slots are observed in both ELFs.
// All ordinary return spellings remain declaration candidates. Source storage,
// constructor adaptation, pointer sizes and native vtable are not ARM ABI.
class FileServerImplementation {
public:
  enum TransferMethod : int {};
  // Original C1/C2 call UCGetFileTransferManager. The service is unresolved;
  // default construction is deliberately not defined by this candidate.
  FileServerImplementation();
  explicit FileServerImplementation(presonus::uc::FileServerPorts &ports)
      : ports_(ports) {}
  virtual void handleRequest(const FileRequestEvent &);
  virtual bool retrieveFile(const FileRequestEvent &);
  virtual bool storeFile(const FileRequestEvent &);
  virtual IFileRequestHandler *retrieveFile(const char *, TransferMethod);
  virtual IFileRequestHandler *storeFile(const char *, TransferMethod) = 0;
  virtual IFileRequestHandler *listDirectory(const char *, const char *) = 0;
  virtual bool deleteFile(const char *) = 0;
  virtual bool renameFile(const char *, const char *) = 0;

protected:
  // No virtual destructor slot occurs in the original table.
  ~FileServerImplementation() = default;

private:
  presonus::uc::FileServerPorts &ports_;
};
} // namespace Presonus::UC
