#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

using namespace Presonus::UC;
namespace presonus::uc {
struct FileTransferStateAccess {
  static auto words(const FileTransfer &t) { return t.words; }
  static auto *handler(const FileTransfer &t) { return t.handler; }
  static void seed(FileTransfer &t, std::uint32_t a, std::uint32_t b,
                   std::uint32_t id) {
    t.words[0] = a;
    t.words[1] = b;
    t.words[2] = id;
  }
};
struct FileTransferManagerStateAccess {
  static auto &list(FileTransferManager &m) { return m.transfers_; }
  static void reserve(FileTransferManager &m, unsigned n) {
    for (unsigned i = 0; i < n; ++i)
      if (m.identifiers_.newID() != static_cast<int>(i + 1))
        throw std::runtime_error("ID allocation seed mismatch");
  }
  static int nextID(const FileTransferManager &m) {
    auto copy = m.identifiers_;
    return copy.newID();
  }
};
} // namespace presonus::uc
using Access = presonus::uc::FileTransferStateAccess;
using State = presonus::uc::FileTransferManagerStateAccess;
static std::array<std::int64_t, 2> ticks{};
static unsigned clockCalls = 0;
static std::ostringstream trace;
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  if (clockCalls >= ticks.size())
    throw std::runtime_error("unexpected clock call");
  const auto value = ticks[clockCalls++];
  trace << "T " << value << ';';
  return value;
}
class Sink final : public presonus::uc::TransferManagerTransferSink {
public:
  void sendAbort(const FileAbortEvent &, int) override {
    throw std::runtime_error("unexpected abort");
  }
  void sendData(const FileDataEvent &, int) override {
    throw std::runtime_error("unexpected data");
  }
  void sendRate(const FileDataRateEvent &, int) override {
    throw std::runtime_error("unexpected rate");
  }
  void sendRequest(const FileRequestEvent &event, int flags) override {
    trace << "S " << event.header.type << ' ' << event.header.reserved04 << ' '
          << event.header.routeA << ' ' << event.header.routeB << ' '
          << event.idBits << ' ' << event.requestBits << ' ' << flags << ';';
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
    throw std::runtime_error("not in request corpus");
  }
};
class Handler final : public IFileRequestHandler {
public:
  bool readData(FileDataEvent &) override {
    throw std::runtime_error("unexpected read");
  }
  bool writeData(const FileDataEvent &) override {
    throw std::runtime_error("unexpected write");
  }
  void finish() override {}
};
static int signedBits(std::uint32_t value) {
  int result;
  static_assert(sizeof(result) == sizeof(value));
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
int main() {
  try {
    unsigned operation, used, existing, handlerPresent;
    std::uint32_t flags, a, b, id, code;
    while (std::cin >> operation >> used >> existing >> handlerPresent >>
           flags >> ticks[0] >> ticks[1] >> a >> b >> id >> code) {
      if (operation > 1 || used > 257 || existing > 2 || handlerPresent > 1)
        throw std::runtime_error("fixture exceeds bounded domain");
      Sink sink;
      Manager manager(sink);
      State::reserve(manager, used);
      for (unsigned n = 0; n < existing; ++n) {
        auto *value = new FileTransfer;
        Access::seed(*value, n + 100, n + 200, n + 300);
        State::list(manager).append(value);
      }
      FileRequestEvent event;
      event.header = {0x4652, 536, a, b};
      event.idBits = id;
      event.requestBits = code;
      for (unsigned n = 0; n < 2; ++n)
        for (unsigned j = 0; j < 255; ++j)
          event.strings[n][j] = static_cast<char>((j * 73 + n * 31) % 255 + 1);
      const auto before = event;
      Handler handler;
      clockCalls = 0;
      trace.str("");
      trace.clear();
      const int result =
          operation == 0
              ? manager.sendRequest(event, handlerPresent ? &handler : nullptr,
                                    signedBits(flags))
              : manager.acceptRequest(handlerPresent ? &handler : nullptr,
                                      signedBits(flags), event);
      auto expectedEvent = before;
      expectedEvent.idBits = event.idBits;
      if (operation == 1 && event.idBits != before.idBits)
        throw std::runtime_error("const request ID changed");
      if (std::memcmp(&event, &expectedEvent, sizeof(event)))
        throw std::runtime_error("request changed outside ID");
      std::cout << result << '|' << event.idBits << '|' << clockCalls << '|'
                << trace.str() << '|' << State::list(manager).count();
      for (Core::ListIterator<FileTransfer *> i(State::list(manager));
           !i.done();) {
        auto *value = i.next();
        std::cout << ' ' << (Access::handler(*value) == &handler);
        for (auto word : Access::words(*value))
          std::cout << ' ' << word;
      }
      std::cout << '|' << State::nextID(manager) << "|1\n";
      while (!State::list(manager).isEmpty())
        delete State::list(manager).removeFirst();
    }
    if (!std::cin.eof())
      throw std::runtime_error("malformed input");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
