#include "core/public/corememstream.h"
#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

namespace presonus::uc {
struct FileTransferStateAccess {
  static auto words(const Presonus::UC::FileTransfer &value) {
    return value.words;
  }
  static void words(Presonus::UC::FileTransfer &value,
                    const std::array<std::uint32_t, 14> &words) {
    value.words = words;
  }
  static void handler(Presonus::UC::FileTransfer &value,
                      Presonus::UC::IFileRequestHandler *handler) {
    value.handler = handler;
  }
  static bool hasHandler(const Presonus::UC::FileTransfer &value) {
    return value.handler != nullptr;
  }
};
} // namespace presonus::uc
using namespace Presonus::UC;
using Access = presonus::uc::FileTransferStateAccess;
extern "C" void ctorC1(void *) asm("_ZN8Presonus2UC12FileTransferC1Ev");
extern "C" void ctorC2(void *) asm("_ZN8Presonus2UC12FileTransferC2Ev");
extern "C" void dtorD1(void *) asm("_ZN8Presonus2UC12FileTransferD1Ev");
extern "C" void dtorD2(void *) asm("_ZN8Presonus2UC12FileTransferD2Ev");

static bool trackAllocation = false;
static unsigned allocationCalls = 0;
static std::size_t allocationSize = 0;
static unsigned char allocationFill = 0;
static void *observedObject = nullptr;
static void *observedHandler = nullptr;
static void *observedStream = nullptr;
static unsigned objectDeletes = 0, handlerDeletes = 0, streamDeletes = 0,
                deleteDepth = 0;
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *result = __real__Znwm(size);
  if (trackAllocation) {
    ++allocationCalls;
    allocationSize = size;
    std::memset(result, allocationFill, size);
  }
  return result;
}
static void observeDelete(void *pointer) {
  if (deleteDepth++ != 0)
    return;
  if (pointer == observedObject)
    ++objectDeletes;
  if (pointer == observedHandler)
    ++handlerDeletes;
  if (pointer == observedStream)
    ++streamDeletes;
}
extern "C" void __wrap__ZdlPv(void *pointer) {
  observeDelete(pointer);
  __real__ZdlPv(pointer);
  --deleteDepth;
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  observeDelete(pointer);
  __real__ZdlPvm(pointer, size);
  --deleteDepth;
}
static unsigned finishCalls = 0, captureDestroyed = 0;
class Capture final : public IFileRequestHandler {
public:
  ~Capture() { ++captureDestroyed; }
  bool readData(FileDataEvent &) override { return false; }
  bool writeData(const FileDataEvent &) override { return false; }
  void finish() override { ++finishCalls; }
};
static void snapshot(const FileTransfer &transfer) {
  for (auto value : Access::words(transfer))
    std::cout << value << ' ';
  std::cout << Access::hasHandler(transfer);
}
int main() {
  try {
    char operation;
    while (std::cin >> operation) {
      observedObject = observedHandler = observedStream = nullptr;
      objectDeletes = handlerDeletes = streamDeletes = 0;
      finishCalls = captureDestroyed = 0;
      if (operation == 'c') {
        unsigned variant, fill;
        std::cin >> variant >> fill;
        alignas(FileTransfer) std::array<unsigned char, sizeof(FileTransfer)>
            storage;
        storage.fill(static_cast<unsigned char>(fill));
        (variant == 1 ? ctorC1 : ctorC2)(storage.data());
        auto *transfer = reinterpret_cast<FileTransfer *>(storage.data());
        std::cout << "c ";
        snapshot(*transfer);
        std::cout << '\n';
        dtorD1(transfer);
      } else if (operation == 'd') {
        unsigned variant, present, fill;
        std::cin >> variant >> present >> fill;
        std::array<std::uint32_t, 14> values;
        for (auto &value : values)
          std::cin >> value;
        alignas(FileTransfer) std::array<unsigned char, sizeof(FileTransfer)>
            storage;
        storage.fill(static_cast<unsigned char>(fill));
        ctorC1(storage.data());
        auto *transfer = reinterpret_cast<FileTransfer *>(storage.data());
        Capture capture;
        Access::words(*transfer, values);
        Access::handler(*transfer, present ? &capture : nullptr);
        const auto before = storage;
        observedObject = transfer;
        (variant == 1 ? dtorD1 : dtorD2)(transfer);
        std::cout << "d " << finishCalls << ' ' << captureDestroyed << ' '
                  << objectDeletes << ' ' << (storage == before) << '\n';
        observedObject = nullptr;
      } else if (operation == 'f') {
        std::uint32_t routeA, routeB, id;
        unsigned reverse, fill;
        std::cin >> routeA >> routeB >> id >> reverse >> fill;
        FileRequestEvent request;
        request.header.routeA = routeA;
        request.header.routeB = routeB;
        request.idBits = id;
        allocationCalls = 0;
        allocationSize = 0;
        allocationFill = static_cast<unsigned char>(fill);
        trackAllocation = true;
        auto *transfer = FileTransfer::create(request, reverse != 0);
        trackAllocation = false;
        std::cout << "f ";
        snapshot(*transfer);
        std::cout << ' ' << allocationCalls << ' ' << allocationSize << '\n';
        observedObject = transfer;
        delete transfer;
        if (objectDeletes != 1)
          throw std::runtime_error(
              "factory object was not actually deallocated once");
        observedObject = nullptr;
      } else if (operation == 's') {
        auto *stream = new Core::IO::MemoryStream;
        const char payload[] = "source-backed";
        char readback[sizeof(payload)]{};
        if (stream->writeBytes(payload, sizeof(payload)) != sizeof(payload) ||
            stream->setPosition(0, 0) != 0 ||
            stream->readBytes(readback, sizeof(readback)) != sizeof(readback) ||
            std::memcmp(payload, readback, sizeof(payload)) != 0)
          throw std::runtime_error("actual CCL MemoryStream provider failed");
        auto *handler = new FileReader(stream, sizeof(payload));
        observedHandler = handler;
        observedStream = stream;
        {
          FileTransfer transfer;
          Access::handler(transfer, handler);
        }
        if (handlerDeletes != 1 || streamDeletes != 1)
          throw std::runtime_error(
              "finish did not forward actual handler/CCL cleanup");
        std::cout << "s " << handlerDeletes << ' ' << streamDeletes << '\n';
        observedHandler = observedStream = nullptr;
      } else
        throw std::runtime_error("unsupported fixture operation");
      if (!std::cin)
        throw std::runtime_error("truncated fixture");
    }
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 2;
  }
}
