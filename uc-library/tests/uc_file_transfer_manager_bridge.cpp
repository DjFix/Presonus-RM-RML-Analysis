#include "core/public/corememstream.h"
#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace Presonus::UC;
namespace presonus::uc {
struct FileTransferStateAccess {
  static auto &words(FileTransfer &t) { return t.words; }
  static auto words(const FileTransfer &t) { return t.words; }
  static void handler(FileTransfer &t, IFileRequestHandler *p) {
    t.handler = p;
  }
  static auto *handler(const FileTransfer &t) { return t.handler; }
};
struct FileTransferManagerStateAccess {
  static void attach(FileTransferManager &m, FileTransfer *t) {
    m.transfers_.append(t);
  }
  static auto &list(FileTransferManager &m) { return m.transfers_; }
  static void seed(FileTransferManager &m, int burst, bool reporting,
                   unsigned used) {
    m.burst_ = burst;
    m.reporting_ = reporting;
    for (unsigned i = 0; i < used; ++i)
      if (m.identifiers_.newID() != static_cast<int>(i + 1))
        throw std::runtime_error("CCL identifier seed mismatch");
  }
  static int burst(const FileTransferManager &m) { return m.burst_; }
  static bool reporting(const FileTransferManager &m) { return m.reporting_; }
  static std::array<int, 24> probe(const FileTransferManager &m) {
    auto copy = m.identifiers_;
    std::array<int, 24> result{};
    for (auto &id : result)
      id = copy.newID();
    return result;
  }
};
} // namespace presonus::uc
using Access = presonus::uc::FileTransferStateAccess;
using State = presonus::uc::FileTransferManagerStateAccess;
static std::map<const void *, unsigned> observed;
static std::ostringstream trace;
static bool tracking = false;
static unsigned deleteDepth = 0;
static void *providerStream = nullptr, *providerHandler = nullptr;
static unsigned streamDeletes = 0, handlerDeletes = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static void observe(void *p) {
  if (p && p == providerStream) {
    ++streamDeletes;
    providerStream = nullptr;
  }
  if (p && p == providerHandler) {
    ++handlerDeletes;
    providerHandler = nullptr;
  }
  if (!tracking)
    return;
  auto found = observed.find(p);
  if (found != observed.end()) {
    const auto id = found->second;
    observed.erase(found);
    trace << "D " << id << ';';
  }
}
extern "C" void __wrap__ZdlPv(void *p) {
  if (deleteDepth++ == 0)
    observe(p);
  __real__ZdlPv(p);
  --deleteDepth;
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (deleteDepth++ == 0)
    observe(p);
  __real__ZdlPvm(p, size);
  --deleteDepth;
}
class Sink final : public presonus::uc::TransferManagerSink {
public:
  void sendAbort(const FileAbortEvent &e, int flags) override {
    trace << "A " << e.header.type << ' ' << e.header.reserved04 << ' '
          << e.header.routeA << ' ' << e.header.routeB << ' ' << e.idBits << ' '
          << flags << ';';
  }
  void report(presonus::uc::FileTransferReport kind, std::uint32_t id,
              std::uint32_t a, std::uint32_t b) override {
    trace << "L " << static_cast<int>(kind) << ' ' << id << ' ' << a << ' ' << b
          << ';';
  }
};
class Manager final : public FileTransferManager {
public:
  explicit Manager(Sink &sink) : FileTransferManager(sink) {}
  int handleEvent(void *, const Event &) override {
    throw std::runtime_error("unrecovered method invoked");
  }
  int sendRequest(FileRequestEvent &, IFileRequestHandler *, int) override {
    throw std::runtime_error("unrecovered method invoked");
  }
  int acceptRequest(IFileRequestHandler *, int,
                    const FileRequestEvent &) override {
    throw std::runtime_error("unrecovered method invoked");
  }
};
class Handler final : public IFileRequestHandler {
public:
  explicit Handler(unsigned id) : id(id) {}
  bool readData(FileDataEvent &) override {
    throw std::runtime_error("unexpected read");
  }
  bool writeData(const FileDataEvent &) override {
    throw std::runtime_error("unexpected write");
  }
  void finish() override {
    if (tracking)
      trace << "F " << id << ';';
  }
  unsigned id;
};
static int signedBits(std::uint32_t value) {
  std::int32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
static unsigned token(IFileRequestHandler *p,
                      std::array<Handler, 3> &handlers) {
  if (!p)
    return 0;
  for (auto &h : handlers)
    if (p == &h)
      return h.id;
  throw std::runtime_error("unknown handler pointer");
}
int main(int argc, char **argv) {
  try {
    if (argc == 2 && std::string(argv[1]) == "--provider-smoke") {
      Sink sink;
      Manager manager(sink);
      auto *stream = new Core::IO::MemoryStream;
      stream->writeBytes("real", 4);
      stream->setPosition(0, 0);
      providerStream = stream;
      auto *handler = new FileReader(stream, 4);
      providerHandler = handler;
      FileDataEvent data;
      if (!handler->readData(data) || data.count != 4 ||
          std::memcmp(data.data.data(), "real", 4))
        throw std::runtime_error("actual CCL stream mismatch");
      auto *value = new FileTransfer;
      Access::handler(*value, handler);
      State::attach(manager, value);
      observed[value] = 1;
      tracking = true;
      manager.remove(value);
      tracking = false;
      if (!observed.empty() || handlerDeletes != 1 || streamDeletes != 1 ||
          manager.isBusy())
        throw std::runtime_error(
            "actual handler/stream/object cleanup mismatch");
      std::cout
          << "actual CCL read + manager removal/handler/stream cleanup PASS\n";
      return 0;
    }
    unsigned op, count, used, reporting, queryHandler, aux;
    std::uint32_t burst, arg, routeA, routeB, id;
    while (std::cin >> op >> count >> used >> burst >> reporting >>
           queryHandler >> arg >> aux >> routeA >> routeB >> id) {
      if (count > 4 || used > 256 || queryHandler > 3 || reporting > 1 ||
          aux > 255)
        throw std::runtime_error("fixture exceeds bounded domain");
      Sink sink;
      Manager manager(sink);
      State::seed(manager, signedBits(burst), reporting != 0, used);
      std::array<Handler, 3> handlers{Handler(1), Handler(2), Handler(3)};
      observed.clear();
      std::array<FileTransfer *, 4> values{};
      for (unsigned n = 0; n < count; ++n) {
        auto *value = new FileTransfer;
        for (auto &word : Access::words(*value))
          std::cin >> word;
        unsigned handler;
        std::cin >> handler;
        if (handler > 3)
          throw std::runtime_error("bad handler token");
        Access::handler(*value, handler ? &handlers[handler - 1] : nullptr);
        State::attach(manager, value);
        observed[value] = n + 1;
        values[n] = value;
      }
      trace.str("");
      trace.clear();
      tracking = true;
      int result = -2;
      auto *handler = queryHandler ? &handlers[queryHandler - 1] : nullptr;
      if (op == 0) {
        FileTransferEvent event;
        event.header.routeA = routeA;
        event.header.routeB = routeB;
        event.idBits = id;
        auto *found = manager.find(event);
        result = found ? static_cast<int>(observed.at(found)) : -1;
      } else if (op == 1) {
        auto *found = manager.find(handler);
        result = found ? static_cast<int>(observed.at(found)) : -1;
      } else if (op == 2)
        result = manager.isBusy();
      else if (op == 3)
        result = manager.setTransferPriority(signedBits(arg));
      else if (op == 4)
        result = manager.setDataRateLimit(handler, signedBits(arg));
      else if (op == 5)
        result =
            manager.enableDataRateReporting(static_cast<unsigned char>(aux));
      else if (op == 6 || op == 7) {
        if (arg >= count)
          throw std::runtime_error("invalid transfer selection");
        if (op == 6)
          manager.remove(values[arg]);
        else
          manager.sendCancel(values[arg]);
      } else if (op == 8)
        manager.cancelAll();
      else if (op == 9)
        result = manager.sendCancel(handler);
      else if (op == 10)
        result = manager.cancelForHandler(signedBits(arg),
                                          static_cast<unsigned char>(aux));
      else
        throw std::runtime_error("bad operation");
      tracking = false;
      std::cout << result << '|' << State::burst(manager) << '|'
                << State::reporting(manager) << '|' << trace.str() << '|';
      auto &list = State::list(manager);
      std::cout << list.count();
      for (Core::ListIterator<FileTransfer *> i(list); !i.done();) {
        auto *value = i.next();
        std::cout << ' ' << observed.at(value) << ' '
                  << token(Access::handler(*value), handlers);
        for (auto word : Access::words(*value))
          std::cout << ' ' << word;
      }
      std::cout << '|';
      for (auto value : State::probe(manager))
        std::cout << value << ' ';
      std::cout << '\n';
      while (!list.isEmpty())
        delete list.removeFirst();
      observed.clear();
    }
    if (!std::cin.eof())
      throw std::runtime_error("malformed fixture");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
