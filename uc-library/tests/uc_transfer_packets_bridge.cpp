#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>

using namespace Presonus::UC;
namespace presonus::uc {
struct FileTransferStateAccess {
  static auto &words(FileTransfer &t) { return t.words; }
  static auto *handler(const FileTransfer &t) { return t.handler; }
  static void handler(FileTransfer &t, IFileRequestHandler *h) {
    t.handler = h;
  }
};
struct FileTransferManagerStateAccess {
  static auto &list(FileTransferManager &m) { return m.transfers_; }
  static void seed(FileTransferManager &m, unsigned used, int burst,
                   bool report, std::int64_t last) {
    m.burst_ = burst;
    m.reporting_ = report;
    m.lastReport_ = last;
    for (unsigned i = 0; i < used; ++i)
      if (m.identifiers_.newID() != static_cast<int>(i + 1))
        throw std::runtime_error("ID seed mismatch");
  }
  static std::int64_t last(const FileTransferManager &m) {
    return m.lastReport_;
  }
  static auto ids(const FileTransferManager &m) {
    auto copy = m.identifiers_;
    std::array<int, 4> result{};
    for (auto &id : result)
      id = copy.newID();
    return result;
  }
};
} // namespace presonus::uc
using Access = presonus::uc::FileTransferStateAccess;
using State = presonus::uc::FileTransferManagerStateAccess;
static std::ostringstream trace;
static std::int64_t tick;
static unsigned clockCalls;
static bool tracking;
static std::map<const void *, unsigned> live;
static unsigned deleteDepth;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static void deleted(void *p) {
  if (!tracking)
    return;
  auto found = live.find(p);
  if (found != live.end()) {
    const auto id = found->second;
    live.erase(found);
    trace << "X " << id << ';';
  }
}
extern "C" void __wrap__ZdlPv(void *p) {
  if (deleteDepth++ == 0)
    deleted(p);
  __real__ZdlPv(p);
  --deleteDepth;
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (deleteDepth++ == 0)
    deleted(p);
  __real__ZdlPvm(p, n);
  --deleteDepth;
}
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  if (++clockCalls > 64)
    throw std::runtime_error("clock bound");
  trace << "T " << tick << ';';
  return tick;
}
static void fill(FileDataEvent &e, unsigned seed) {
  if (e.count > 64)
    throw std::runtime_error("payload fixture bound");
  for (unsigned i = 0; i < e.count; ++i)
    e.data[i] = static_cast<unsigned char>(seed + i * 73);
}
static void data(const char *kind, const FileDataEvent &e) {
  trace << kind << ' ' << e.header.type << ' ' << e.header.reserved04 << ' '
        << e.header.routeA << ' ' << e.header.routeB << ' ' << e.idBits << ' '
        << e.wordBits[0] << ' ' << e.wordBits[1] << ' ' << e.partBits << ' '
        << e.count << ' ';
  const char digits[] = "0123456789abcdef";
  if (!e.count)
    trace << '-';
  for (unsigned i = 0; i < e.count; ++i)
    trace << digits[e.data[i] >> 4] << digits[e.data[i] & 15];
  trace << ';';
}
struct Step {
  unsigned result, status, count, seed;
};
class Handler final : public IFileRequestHandler {
public:
  unsigned id = 0, cursor = 0, writeResult = 0;
  std::array<Step, 4> steps{};
  bool readData(FileDataEvent &e) override {
    if (cursor >= steps.size())
      throw std::runtime_error("read bound");
    const auto s = steps[cursor++];
    e.partBits = s.status;
    e.count = s.count;
    e.wordBits = {cursor * 17, id * 23};
    fill(e, s.seed);
    trace << "R " << id << ' ' << cursor << ' ' << s.result << ';';
    return s.result != 0;
  }
  bool writeData(const FileDataEvent &e) override {
    trace << "W " << id << ' ' << writeResult << ';';
    data("w", e);
    return writeResult != 0;
  }
  void finish() override {
    if (tracking)
      trace << "F " << id << ';';
  }
};
class Sink final : public presonus::uc::TransferManagerTransferSink {
public:
  FileTransferManager *manager = nullptr;
  bool reenter = false;
  void sendRequest(const FileRequestEvent &, int) override {
    throw std::runtime_error("unexpected request");
  }
  void sendAbort(const FileAbortEvent &e, int flags) override {
    trace << "A " << e.header.type << ' ' << e.header.reserved04 << ' '
          << e.header.routeA << ' ' << e.header.routeB << ' ' << e.idBits << ' '
          << flags << ';';
  }
  void sendData(const FileDataEvent &e, int flags) override {
    if (flags)
      throw std::runtime_error("data flags");
    data("D", e);
    if (reenter) {
      reenter = false;
      trace << "I;";
      manager->processIdle();
    }
  }
  void sendRate(const FileDataRateEvent &e, int flags) override {
    trace << "S " << e.header.type << ' ' << e.header.reserved04 << ' '
          << e.header.routeA << ' ' << e.header.routeB << ' ' << e.idBits;
    for (auto w : e.wordBits)
      trace << ' ' << w;
    trace << ' ' << flags << ';';
  }
  void report(presonus::uc::FileTransferReport kind, std::uint32_t id,
              std::uint32_t a, std::uint32_t b) override {
    trace << "L " << static_cast<int>(kind) << ' ' << id;
    if (kind == presonus::uc::FileTransferReport::CancelAll ||
        kind == presonus::uc::FileTransferReport::CancelHandler)
      trace << ' ' << a << ' ' << b;
    trace << ';';
  }
};
static int signedBits(std::uint32_t bits) {
  int v;
  std::memcpy(&v, &bits, 4);
  return v;
}
int main() {
  try {
    unsigned imageRole, op, count, used, report, selected, reenter, part,
        payloadCount, seed;
    std::uint32_t burst, param, type, routeA, routeB, id, w0, w1, w2;
    std::int64_t last;
    while (std::cin >> imageRole >> op >> count >> used >> burst >> report >>
           tick >> last >> param >> selected >> reenter >> type >> routeA >>
           routeB >> id >> w0 >> w1 >> w2 >> part >> payloadCount >> seed) {
      if (count > 3 || used > 256 || report > 1 || reenter > 1 ||
          payloadCount > 64 || op > 3 || (op < 2 && selected >= count))
        throw std::runtime_error("fixture bound");
      Sink sink;
      if (imageRole > 1)
        throw std::runtime_error("image role bound");
      FileTransferManager manager(
          sink, imageRole == 0 ? presonus::uc::TransferManagerImageRole::CS18
                               : presonus::uc::TransferManagerImageRole::RM);
      sink.manager = &manager;
      sink.reenter = reenter;
      State::seed(manager, used, signedBits(burst), report != 0, last);
      std::array<Handler, 3> handlers;
      for (unsigned n = 0; n < handlers.size(); ++n)
        handlers[n].id = n + 1;
      std::array<FileTransfer *, 3> values{};
      live.clear();
      for (unsigned n = 0; n < count; ++n) {
        auto *value = new FileTransfer;
        for (auto &word : Access::words(*value))
          std::cin >> word;
        unsigned token;
        std::cin >> token;
        if (token < 1 || token > 3)
          throw std::runtime_error("handler token");
        Access::handler(*value, &handlers[token - 1]);
        State::list(manager).append(value);
        values[n] = value;
        live[value] = n + 1;
      }
      for (auto &h : handlers) {
        std::cin >> h.writeResult;
        for (auto &s : h.steps)
          std::cin >> s.result >> s.status >> s.count >> s.seed;
      }
      FileDataEvent event;
      event.header = {type, 4128, routeA, routeB};
      event.idBits = id;
      event.wordBits = {w0, w1};
      event.partBits = part;
      event.count = payloadCount;
      fill(event, seed);
      FileDataRateEvent rate;
      rate.header = {type, 32, routeA, routeB};
      rate.idBits = id;
      rate.wordBits = {w0, w1, w2};
      FileAbortEvent abort;
      abort.header = {type, 20, routeA, routeB};
      abort.idBits = id;
      trace.str("");
      trace.clear();
      clockCalls = 0;
      tracking = true;
      int result = -2;
      if (op == 0)
        result = manager.processRead(values[selected]);
      else if (op == 1)
        manager.sendDataRate(values[selected], tick / 1000000,
                             signedBits(param));
      else if (op == 2)
        result = manager.handleEvent(nullptr, type == 0x4653   ? rate.header
                                              : type == 0x4641 ? abort.header
                                                               : event.header);
      else
        manager.processIdle();
      tracking = false;
      std::cout << result << '|' << clockCalls << '|' << State::last(manager)
                << '|' << trace.str() << '|' << State::list(manager).count();
      for (Core::ListIterator<FileTransfer *> i(State::list(manager));
           !i.done();) {
        auto *value = i.next();
        auto *h = static_cast<Handler *>(Access::handler(*value));
        std::cout << ' ' << live.at(value) << ' ' << h->id;
        for (auto word : Access::words(*value))
          std::cout << ' ' << word;
      }
      std::cout << '|';
      for (const auto &h : handlers)
        std::cout << h.cursor << ' ';
      std::cout << '|';
      for (auto x : State::ids(manager))
        std::cout << x << ' ';
      std::cout << '\n';
      while (!State::list(manager).isEmpty())
        delete State::list(manager).removeFirst();
      live.clear();
    }
    if (!std::cin.eof())
      throw std::runtime_error("malformed input");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
