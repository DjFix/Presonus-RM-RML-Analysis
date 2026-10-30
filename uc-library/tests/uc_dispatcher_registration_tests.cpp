#include "presonus/uc/event_dispatcher.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace Presonus::UC;
using namespace presonus::uc;
constexpr unsigned none = 0xffffffffu;
using Pair = std::array<unsigned, 2>;
using Row = std::array<unsigned, 8>;
static void require(bool v) {
  if (!v)
    throw std::runtime_error("registration fixture mismatch");
}
static int signedBits(unsigned n) {
  int v;
  std::memcpy(&v, &n, 4);
  return v;
}
static unsigned readWord(std::ifstream &f) {
  std::array<unsigned char, 4> b{};
  f.read(reinterpret_cast<char *>(b.data()), 4);
  require(bool(f));
  return unsigned(b[0]) | (unsigned(b[1]) << 8) | (unsigned(b[2]) << 16) |
         (unsigned(b[3]) << 24);
}
static std::vector<unsigned> sequence(std::ifstream &f) {
  std::vector<unsigned> out(readWord(f));
  for (auto &v : out)
    v = readWord(f);
  return out;
}
static std::vector<Pair> pairs(std::ifstream &f) {
  std::vector<Pair> out(readWord(f));
  for (auto &p : out)
    for (auto &v : p)
      v = readWord(f);
  return out;
}
struct Handler : IEventHandler {
  int handleEvent(void *, const Event &) override {
    throw std::runtime_error("registration must not call handler");
  }
};
struct Context {
  EventDispatcherState state;
  EventDispatcher dispatcher{state};
  std::array<Handler, 3> handlers;
  unsigned depth = 0;
  std::vector<Row> trace;
  explicit Context(int modulus) : state(modulus) {
    state.auditContext = this;
    state.audit = [](void *p, DispatcherAudit stage) {
      auto &c = *static_cast<Context *>(p);
      unsigned s = unsigned(stage);
      require(s == 1 || s == 2);
      if (s == 1) {
        ++c.depth;
        require(c.depth <= 2);
      } else
        require(c.depth > 0);
      auto entries = c.entries();
      Pair first = entries.empty() ? Pair{none, none} : entries.front();
      c.trace.push_back({s, c.depth, unsigned(c.state.handlers.count()),
                         unsigned(c.state.externalIDs.count()),
                         c.hid(c.state.fallback), first[0], first[1], 0});
      if (s == 2)
        --c.depth;
    };
  }
  IEventHandler *handler(unsigned id) {
    return id == none ? nullptr : &handlers.at(id);
  }
  unsigned hid(IEventHandler *p) const {
    if (!p)
      return none;
    for (unsigned i = 0; i < handlers.size(); ++i)
      if (p == &handlers[i])
        return i;
    throw std::runtime_error("unknown handler");
  }
  std::vector<Pair> entries() const {
    std::vector<Pair> out;
    Core::HashMapIterator<int, IEventHandler *> it(state.handlers);
    while (!it.done()) {
      const auto &a = it.nextAssociation();
      out.push_back({unsigned(a.key), hid(a.value)});
    }
    return out;
  }
  std::vector<unsigned> external() const {
    std::vector<unsigned> out;
    for (int i = 0; i < state.externalIDs.count(); ++i)
      out.push_back(unsigned(state.externalIDs.at(i)));
    return out;
  }
  std::array<unsigned, 4> probes() const {
    // IDSet's genuine source copy constructor deep-copies its BitSet/Vector.
    // Probe the copy, leaving live registration allocator state unchanged.
    Core::IDSet copy(state.identifiers);
    std::array<unsigned, 4> out;
    for (auto &v : out)
      v = unsigned(copy.newID());
    return out;
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  char magic[8];
  f.read(magic, 8);
  require(!std::memcmp(magic, "UCRGv001", 8));
  unsigned count = readWord(f), actionsRun = 0;
  for (unsigned index = 0; index < count; ++index) {
    unsigned role = readWord(f), mod = readWord(f), reserved = readWord(f),
             fallback = readWord(f);
    auto holes = sequence(f), external = sequence(f);
    auto entries = pairs(f);
    unsigned n = readWord(f);
    std::vector<std::array<unsigned, 4>> actions(n);
    for (auto &a : actions)
      for (auto &v : a)
        v = readWord(f);
    Context c{int(mod)};
    for (unsigned i = 0; i < reserved; ++i)
      require(c.state.identifiers.newID() == int(100 + i));
    for (unsigned hole : holes)
      c.state.identifiers.releaseID(int(100 + hole));
    for (auto a : entries)
      c.state.handlers.add(signedBits(a[0]), c.handler(a[1]));
    for (unsigned id : external)
      require(c.state.externalIDs.add(signedBits(id)));
    c.state.fallback = c.handler(fallback);
    unsigned last = 0;
    for (unsigned ai = 0; ai < actions.size(); ++ai) {
      auto action = actions[ai];
      unsigned expectedResult = readWord(f), expectedFallback = readWord(f),
               expectedTotal = readWord(f);
      auto expectedEntries = pairs(f);
      auto expectedExternal = sequence(f);
      std::array<unsigned, 4> expectedProbes;
      for (auto &v : expectedProbes)
        v = readWord(f);
      unsigned rows = readWord(f);
      std::vector<Row> expectedTrace(rows);
      for (auto &r : expectedTrace)
        for (auto &v : r)
          v = readWord(f);
      c.trace.clear();
      unsigned result = 0, arg = action[3] ? last : action[1];
      switch (action[0]) {
      case 0:
        result = unsigned(
            c.dispatcher.addHandler(c.handler(arg), signedBits(action[2])));
        last = result;
        break;
      case 1:
        result = c.dispatcher.removeHandler(signedBits(arg));
        break;
      case 2:
        result = c.dispatcher.removeHandler(c.handler(arg));
        break;
      default:
        return 3;
      }
      if (result != expectedResult ||
          c.hid(c.state.fallback) != expectedFallback ||
          unsigned(c.state.handlers.count()) != expectedTotal ||
          c.entries() != expectedEntries || c.external() != expectedExternal ||
          c.probes() != expectedProbes || c.trace != expectedTrace || c.depth) {
        std::cerr << "registration mismatch case=" << index << " role=" << role
                  << " action=" << ai << " op=" << action[0]
                  << " result=" << result << '/' << expectedResult
                  << " map=" << c.state.handlers.count() << '/' << expectedTotal
                  << " trace=" << c.trace.size() << '/' << expectedTrace.size()
                  << '\n';
        return 1;
      }
      ++actionsRun;
    }
  }
  require(f.peek() == std::char_traits<char>::eof());
  std::cout
      << count << " original ARM registration cases/" << actionsRun
      << " actions passed with actual CCL IDSet/map/vector/recursive locks\n";
}
