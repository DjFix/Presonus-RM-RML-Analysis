#include "presonus/uc/file_server_service.hpp"

namespace Presonus::UC {
namespace {
constexpr std::uint32_t retrieve = 0x52657472, compressedRetrieve = 0x5a527472;
constexpr std::uint32_t store = 0x53746f72, compressedStore = 0x5a537472;
FileServerImplementation::TransferMethod method(const FileRequestEvent &event) {
  return static_cast<FileServerImplementation::TransferMethod>(
      event.requestBits == compressedRetrieve ||
              event.requestBits == compressedStore
          ? 1
          : 0);
}
} // namespace
bool FileServerImplementation::retrieveFile(const FileRequestEvent &event) {
  auto *handler = retrieveFile(event.strings[0].data(), method(event));
  if (!handler)
    return false;
  ports_.acceptRequest(*handler, 0, event);
  return true;
}
bool FileServerImplementation::storeFile(const FileRequestEvent &event) {
  auto *handler = storeFile(event.strings[0].data(), method(event));
  if (!handler)
    return false;
  ports_.acceptRequest(*handler, 1, event);
  return true;
}
IFileRequestHandler *FileServerImplementation::retrieveFile(const char *,
                                                            TransferMethod) {
  return nullptr;
}
void FileServerImplementation::handleRequest(const FileRequestEvent &event) {
  unsigned short status = 3;
  switch (event.requestBits) {
  case retrieve:
  case compressedRetrieve:
    if (retrieveFile(event))
      return;
    break;
  case store:
  case compressedStore:
    if (storeFile(event))
      return;
    break;
  case 0x4c697374:
    if (auto *handler =
            listDirectory(event.strings[0].data(), event.strings[1].data())) {
      ports_.acceptRequest(*handler, 0, event);
      return;
    }
    break;
  case 0x44656c65:
    if (deleteFile(event.strings[0].data()))
      status = 0;
    break;
  case 0x52656e61:
    if (renameFile(event.strings[0].data(), event.strings[1].data()))
      status = 0;
    break;
  }
  FileDataEvent response;
  response.header.type = 0x4644;
  response.header.reserved04 = 4128;
  response.header.routeA = event.header.routeB;
  response.header.routeB = event.header.routeA;
  response.idBits = event.idBits;
  response.partBits = status;
  ports_.sendDataEvent(response, 0);
}
} // namespace Presonus::UC
