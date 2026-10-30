#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
#include <cstring>

DEFINE_SINGLETON(Presonus::UC::FileTransferManager)

namespace Presonus::UC {
FileTransfer *FileTransferManager::find(const FileTransferEvent &event) const {
  for (Core::ListIterator<FileTransfer *> i(transfers_); !i.done();) {
    auto *value = i.next();
    if (value->words[2] == event.idBits &&
        value->words[0] == event.header.routeB &&
        value->words[1] == event.header.routeA)
      return value;
  }
  return nullptr;
}
FileTransfer *FileTransferManager::find(IFileRequestHandler *handler) const {
  for (Core::ListIterator<FileTransfer *> i(transfers_); !i.done();) {
    auto *value = i.next();
    if (value->handler == handler)
      return value;
  }
  return nullptr;
}
bool FileTransferManager::isBusy() const { return !transfers_.isEmpty(); }
int FileTransferManager::setTransferPriority(int priority) {
  if (priority == 0 || priority == 1)
    burst_ = 1;
  else if (priority == 2)
    burst_ = 4;
  return 0;
}
int FileTransferManager::setDataRateLimit(IFileRequestHandler *handler,
                                          int limit) {
  auto *value = find(handler);
  if (!value)
    return 100;
  const float rate = static_cast<float>(limit);
  static_assert(sizeof(rate) == sizeof(value->words[11]));
  std::memcpy(&value->words[11], &rate, sizeof(rate));
  return 0;
}
int FileTransferManager::enableDataRateReporting(unsigned char enabled) {
  reporting_ = enabled != 0;
  return 0;
}
void FileTransferManager::remove(FileTransfer *value) {
  if ((value->words[3] & 1) != 0) {
    std::int32_t id;
    std::memcpy(&id, &value->words[2], sizeof(id));
    // The original signed ARM subtraction/range guard ignores all negative
    // IDs (including INT_MIN wrapping beyond the allocated range). Avoid an
    // undefined signed subtraction in the source CCL releaseID interface.
    if (id > 0)
      identifiers_.releaseID(id);
  }
  transfers_.remove(value);
  delete value;
}
void FileTransferManager::sendCancel(FileTransfer *value) {
  FileAbortEvent event;
  event.header.type = 0x4641;
  event.header.reserved04 = 20;
  event.header.routeA = value->words[0];
  event.header.routeB = value->words[1];
  event.idBits = value->words[2];
  sink_.sendAbort(event, 0);
  remove(value);
}
void FileTransferManager::cancelAll() {
  while (!transfers_.isEmpty()) {
    auto *value = transfers_.getFirst();
    sink_.report(presonus::uc::FileTransferReport::CancelAll, value->words[2],
                 value->words[0], value->words[1]);
    sendCancel(value);
  }
}
int FileTransferManager::sendCancel(IFileRequestHandler *handler) {
  if (!handler)
    return 101;
  auto *value = find(handler);
  if (!value)
    return 100;
  sink_.report(presonus::uc::FileTransferReport::CancelHandler, value->words[2],
               value->words[0], value->words[1]);
  sendCancel(value);
  return 0;
}
int FileTransferManager::cancelForHandler(int id, unsigned char notify) {
  std::uint32_t bits;
  std::memcpy(&bits, &id, sizeof(bits));
  bool found = false;
  for (Core::ListIterator<FileTransfer *> i(transfers_); !i.done();) {
    auto *value = i.next();
    if (value->words[0] == bits || value->words[1] == bits) {
      if (notify)
        sendCancel(value);
      else
        remove(value);
      found = true;
    }
  }
  return found ? 0 : 100;
}
} // namespace Presonus::UC
