#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corebitset.h"
#include "core/public/corelinkedlist.h"
#include "presonus/uc/event_dispatcher.hpp"
#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/file_data_events.hpp"
#include "presonus/uc/file_transfer.hpp"

namespace Presonus::UC {
// Independent source storage for the observed common event prefix. Original
// field declarations, composition, inheritance and ARM layout are unresolved.
struct FileTransferEvent {
  Event header;
  std::uint32_t idBits = 0;
};
class IFileRequestHandler;
class IFileTransferManager : public IEventHandler {
public:
  virtual int sendRequest(FileRequestEvent &, IFileRequestHandler *, int) = 0;
  virtual int acceptRequest(IFileRequestHandler *, int,
                            const FileRequestEvent &) = 0;
  virtual int sendCancel(IFileRequestHandler *) = 0;
  virtual int cancelForHandler(int, unsigned char) = 0;
  virtual int setTransferPriority(int) = 0;
  virtual int setDataRateLimit(IFileRequestHandler *, int) = 0;
  virtual int enableDataRateReporting(unsigned char) = 0;
  virtual bool isBusy() const = 0;

protected:
  ~IFileTransferManager() = default;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Independent image selection, not an original declaration or ARM field.
enum class TransferManagerImageRole { CS18, RM };
enum class FileTransferReport {
  CancelAll,
  CancelHandler,
  SendRequest,
  AcceptRequest,
  ReadError,
  Timeout,
  Abort,
  TransferError
};
class TransferManagerSink {
public:
  // Independent mandatory ports; original NetworkManager::sendEvent and
  // UCReportMessage implementations are not supplied by these declarations.
  virtual void sendAbort(const Presonus::UC::FileAbortEvent &, int) = 0;
  virtual void report(FileTransferReport, std::uint32_t, std::uint32_t,
                      std::uint32_t) = 0;

protected:
  ~TransferManagerSink() = default;
};
class TransferManagerTransferSink : public TransferManagerSink {
public:
  virtual void sendRequest(const Presonus::UC::FileRequestEvent &, int) = 0;
  virtual void sendData(const Presonus::UC::FileDataEvent &, int) = 0;
  virtual void sendRate(const Presonus::UC::FileDataRateEvent &, int) = 0;
};
struct FileTransferManagerStateAccess;
} // namespace presonus::uc
namespace Presonus::UC {
// Actual measured two-base hierarchy, using the pinned CCL implementation.
// Ordinary bodies use explicit source-bound ports. Original lifecycle and
// singleton gateway remain unresolved; no service or ABI fidelity is implied.
class FileTransferManager
    : public IFileTransferManager,
      public Core::Portable::Singleton<FileTransferManager> {
public:
  FileTransferManager(); // Original C1/C2 remain undefined/unresolved.
  explicit FileTransferManager(presonus::uc::TransferManagerSink &sink)
      : sink_(sink), identifiers_(1, 128) {}
  explicit FileTransferManager(presonus::uc::TransferManagerTransferSink &sink,
                               presonus::uc::TransferManagerImageRole role =
                                   presonus::uc::TransferManagerImageRole::CS18)
      : sink_(sink), identifiers_(1, 128), transferSink_(&sink),
        minimumReceiveRate_(role == presonus::uc::TransferManagerImageRole::CS18
                                ? 0x46800000u
                                : 0x45800000u) {}
  int sendRequest(FileRequestEvent &, IFileRequestHandler *, int) override;
  int acceptRequest(IFileRequestHandler *, int,
                    const FileRequestEvent &) override;
  int handleEvent(void *, const Event &) override;
  bool processRead(FileTransfer *);
  void sendDataRate(FileTransfer *, long long, int);
  void processIdle();
  // Support lifetime only in this milestone, no original destructor proof.
  ~FileTransferManager() override = default;
  FileTransfer *find(const FileTransferEvent &) const;
  FileTransfer *find(IFileRequestHandler *) const;
  bool isBusy() const override;
  int setTransferPriority(int) override;
  int setDataRateLimit(IFileRequestHandler *, int) override;
  int enableDataRateReporting(unsigned char) override;
  void remove(FileTransfer *);
  void sendCancel(FileTransfer *);
  void cancelAll();
  int sendCancel(IFileRequestHandler *) override;
  int cancelForHandler(int, unsigned char) override;

private:
  // Logical source-port state, not original member names/types/native layout.
  presonus::uc::TransferManagerSink &sink_;
  Core::IDSet identifiers_;
  Core::LinkedList<FileTransfer *> transfers_;
  int burst_ = 1;
  bool reporting_ = false;
  presonus::uc::TransferManagerTransferSink *transferSink_ = nullptr;
  std::int64_t lastReport_ = 0;
  std::uint32_t minimumReceiveRate_ = 0x46800000u;
  friend struct presonus::uc::FileTransferManagerStateAccess;
};
} // namespace Presonus::UC
