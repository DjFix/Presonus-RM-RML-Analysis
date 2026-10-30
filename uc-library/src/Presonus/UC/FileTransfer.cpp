#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer.hpp"

namespace Presonus::UC {
FileTransfer::FileTransfer() : words{}, handler(nullptr) {}
FileTransfer::~FileTransfer() {
  if (handler)
    handler->finish();
}
FileTransfer *FileTransfer::create(const FileRequestEvent &request,
                                   bool reverse) {
  auto *transfer = new FileTransfer;
  transfer->words[0] = reverse ? request.header.routeB : request.header.routeA;
  transfer->words[1] = reverse ? request.header.routeA : request.header.routeB;
  transfer->words[2] = request.idBits;
  return transfer;
}
} // namespace Presonus::UC
