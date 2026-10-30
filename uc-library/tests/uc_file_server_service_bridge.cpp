#include "core/public/corememstream.h"
#include "presonus/uc/file_server_service.hpp"
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace Presonus::UC;
static std::string hex(const char *p) {
  const char digits[] = "0123456789abcdef";
  std::string result;
  for (; *p; ++p) {
    const auto b = static_cast<unsigned char>(*p);
    result += digits[b >> 4];
    result += digits[b & 15];
  }
  return result.empty() ? "-" : result;
}
class Handler final : public IFileRequestHandler {
public:
  bool readData(FileDataEvent &) override { return false; }
  bool writeData(const FileDataEvent &) override { return false; }
  void finish() override { throw std::runtime_error("unexpected finish"); }
};
class Ports final : public presonus::uc::FileServerPorts {
public:
  std::ostringstream trace;
  const FileRequestEvent *request = nullptr;
  IFileRequestHandler *handler = nullptr;
  void acceptRequest(IFileRequestHandler &value, int direction,
                     const FileRequestEvent &event) override {
    if (&value != handler || &event != request)
      throw std::runtime_error("wrong borrowed handler/request identity");
    trace << "A " << direction << ';';
  }
  void sendDataEvent(const FileDataEvent &event, int flags) override {
    trace << "N " << event.header.type << ' ' << event.header.reserved04 << ' '
          << event.header.routeA << ' ' << event.header.routeB << ' '
          << event.idBits << ' ' << event.wordBits[0] << ' '
          << event.wordBits[1] << ' ' << event.partBits << ' ' << event.count
          << ' ' << flags << ';';
  }
};
class Server final : public FileServerImplementation {
public:
  Server(Ports &p, Handler &h, unsigned mask)
      : FileServerImplementation(p), ports(p), handler(h), mask(mask) {}
  IFileRequestHandler *retrieveFile(const char *path,
                                    TransferMethod method) override {
    ports.trace << "R " << int(method) << ' ' << hex(path) << ';';
    return mask & 1 ? &handler : nullptr;
  }
  IFileRequestHandler *storeFile(const char *path,
                                 TransferMethod method) override {
    ports.trace << "S " << int(method) << ' ' << hex(path) << ';';
    return mask & 2 ? &handler : nullptr;
  }
  IFileRequestHandler *listDirectory(const char *path,
                                     const char *filter) override {
    ports.trace << "L " << hex(path) << ' ' << hex(filter) << ';';
    return mask & 4 ? &handler : nullptr;
  }
  bool deleteFile(const char *path) override {
    ports.trace << "D " << hex(path) << ';';
    return (mask & 8) != 0;
  }
  bool renameFile(const char *a, const char *b) override {
    ports.trace << "M " << hex(a) << ' ' << hex(b) << ';';
    return (mask & 16) != 0;
  }

private:
  Ports &ports;
  Handler &handler;
  unsigned mask;
};
static void paths(FileRequestEvent &event, unsigned a, unsigned b,
                  unsigned seed) {
  for (unsigned n = 0; n < 2; ++n) {
    const unsigned length = n ? b : a;
    if (length > 255)
      throw std::runtime_error("path exceeds bounded CString domain");
    for (unsigned j = 0; j < length; ++j)
      event.strings[n][j] =
          static_cast<char>((seed + j * 73 + n * 31) % 255 + 1);
  }
}
static int destroyedStreams = 0;
static void *observedStream = nullptr;
static unsigned deleteDepth = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (deleteDepth++ == 0 && p == observedStream)
    ++destroyedStreams;
  __real__ZdlPv(p);
  --deleteDepth;
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (deleteDepth++ == 0 && p == observedStream)
    ++destroyedStreams;
  __real__ZdlPvm(p, size);
  --deleteDepth;
}
class ProviderServer final : public FileServerImplementation {
public:
  explicit ProviderServer(presonus::uc::FileServerPorts &p)
      : FileServerImplementation(p) {}
  IFileRequestHandler *retrieveFile(const char *, TransferMethod) override {
    auto *stream = new Core::IO::MemoryStream;
    observedStream = stream;
    stream->writeBytes("actual-ccl", 10);
    stream->setPosition(0, 0);
    return new FileReader(stream, 10);
  }
  IFileRequestHandler *storeFile(const char *, TransferMethod) override {
    auto *stream = new Core::IO::MemoryStream;
    observedStream = stream;
    return new FileWriter(stream);
  }
  IFileRequestHandler *listDirectory(const char *, const char *) override {
    return nullptr;
  }
  bool deleteFile(const char *) override { return false; }
  bool renameFile(const char *, const char *) override { return false; }
};
class ProviderPorts final : public presonus::uc::FileServerPorts {
public:
  unsigned calls = 0;
  void acceptRequest(IFileRequestHandler &handler, int direction,
                     const FileRequestEvent &) override {
    FileDataEvent data;
    if (direction == 0) {
      if (!handler.readData(data) || data.count != 10 || data.partBits != 0 ||
          std::memcmp(data.data.data(), "actual-ccl", 10))
        throw std::runtime_error("actual CCL reader mismatch");
    } else {
      data.count = 4;
      std::memcpy(data.data.data(), "test", 4);
      if (!handler.writeData(data))
        throw std::runtime_error("actual CCL writer mismatch");
      auto *stream = static_cast<FileRequestHandler &>(handler).getStream();
      char actual[4]{};
      stream->setPosition(0, 0);
      if (stream->readBytes(actual, 4) != 4 || std::memcmp(actual, "test", 4))
        throw std::runtime_error("actual CCL written stream mismatch");
    }
    ++calls;
    handler.finish();
    observedStream = nullptr;
  }
  void sendDataEvent(const FileDataEvent &, int) override {
    throw std::runtime_error("unexpected response");
  }
};
int main(int argc, char **argv) {
  try {
    if (argc == 2 && std::string(argv[1]) == "--provider-smoke") {
      ProviderPorts p;
      ProviderServer server(p);
      FileRequestEvent event;
      event.requestBits = 0x52657472;
      server.handleRequest(event);
      event.requestBits = 0x53746f72;
      server.handleRequest(event);
      if (p.calls != 2 || destroyedStreams != 2)
        throw std::runtime_error("actual provider cleanup mismatch");
      std::cout << "actual CCL read/write and two owned stream cleanups PASS\n";
      return 0;
    }
    unsigned operation, mask, lenA, lenB, seed;
    std::uint32_t code, routeA, routeB, id;
    while (std::cin >> operation >> code >> mask >> routeA >> routeB >> id >>
           lenA >> lenB >> seed) {
      FileRequestEvent event;
      event.header.type = 0x4652;
      event.header.reserved04 = 536;
      event.header.routeA = routeA;
      event.header.routeB = routeB;
      event.idBits = id;
      event.requestBits = code;
      paths(event, lenA, lenB, seed);
      const auto before = event;
      Ports ports;
      Handler handler;
      ports.request = &event;
      ports.handler = &handler;
      Server server(ports, handler, mask);
      int returned = -1;
      if (operation == 0)
        returned = server.FileServerImplementation::retrieveFile(event);
      else if (operation == 1)
        returned = server.FileServerImplementation::storeFile(event);
      else if (operation == 2)
        returned =
            server.FileServerImplementation::retrieveFile(
                event.strings[0].data(),
                static_cast<FileServerImplementation::TransferMethod>(mask)) !=
            nullptr;
      else if (operation == 3)
        server.handleRequest(event);
      else
        throw std::runtime_error("bad operation");
      if (std::memcmp(&event, &before, sizeof(event)))
        throw std::runtime_error("request mutated");
      std::cout << returned << '|' << ports.trace.str() << "|1\n";
    }
    if (!std::cin.eof())
      throw std::runtime_error("malformed fixture");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
