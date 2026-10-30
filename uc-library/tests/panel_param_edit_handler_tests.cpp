#include "presonus/panel/param_edit_handler.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <new>
#include <type_traits>
#include <vector>

using Handler = Presonus::Panel::ParamEditHandler;
using Access = presonus::panel::ParamEditHandlerAccess;
using Core::Portable::Parameter;
using Event = std::array<std::uint32_t, 4>;
namespace {
struct Allocation {
  void *pointer{};
  unsigned kind{}, bytes{};
};
struct Context {
  bool active{};
  unsigned op{}, fail{}, attempts{}, clockCalls{};
  std::int64_t ticks{};
  std::array<Allocation, 6> allocations{};
  std::vector<Event> events;
} context;
void event(unsigned a, unsigned b = 0, unsigned c = 0, unsigned d = 0) {
  context.events.push_back({a, b, c, d});
}
void remember(void *p, unsigned kind, unsigned bytes) {
  if (!p)
    return;
  for (auto &a : context.allocations)
    if (!a.pointer) {
      a = {p, kind, bytes};
      return;
    }
  std::abort();
}
void deleting(void *p) {
  if (!context.active || !p)
    return;
  for (auto &a : context.allocations)
    if (a.pointer == p) {
      event(9, a.kind, a.bytes);
      a = {};
      return;
    }
}
struct Param : Core::Portable::NumericParam {
  unsigned identity;
  Param(const Core::Portable::ParamInfo &info, unsigned id)
      : NumericParam(info), identity(id) {}
  bool isEditing() const override {
    const bool state = Parameter::isEditing();
    if (context.active)
      event(3, identity, state);
    return state;
  }
  void beginEdit() override {
    if (context.active)
      event(4, identity, Parameter::isEditing());
    Parameter::beginEdit();
  }
  void endEdit() override {
    if (context.active)
      event(5, identity, Parameter::isEditing());
    Parameter::endEdit();
  }
};
struct Controller : Core::Portable::ParamObserverBase {
  void paramChanged(Parameter *p, int message) override {
    if (context.active) {
      auto *value = static_cast<Param *>(p);
      event(7, value->identity, unsigned(message), p->Parameter::isEditing());
    }
  }
};
std::uint32_t word(const unsigned char *p) {
  std::uint32_t v;
  std::memcpy(&v, p, 4);
  return v;
}
std::uint64_t wide(const unsigned char *p) {
  std::uint64_t v;
  std::memcpy(&v, p, 8);
  return v;
}
double real(std::uint64_t bits) {
  double v;
  std::memcpy(&v, &bits, 8);
  return v;
}
std::uint64_t bits(double v) {
  std::uint64_t result;
  std::memcpy(&result, &v, 8);
  return result;
}
void append(std::vector<unsigned char> &out, std::uint64_t value,
            unsigned size) {
  for (unsigned i = 0; i < size; ++i)
    out.push_back(static_cast<unsigned char>(value >> (8 * i)));
}
struct Row {
  unsigned identity;
  std::uint64_t time;
};
struct Snapshot {
  std::array<unsigned, 4> header;
  std::vector<Row> rows;
};
template <class Vector, class Id>
Snapshot snapshot(Vector &values, unsigned initial, Id identity) {
  Snapshot s{{unsigned(values.count()), unsigned(values.getCapacity()),
              unsigned(values.getDelta()),
              unsigned(values.getItems() != nullptr)},
             {}};
  const unsigned size =
      std::min(std::max(initial, unsigned(values.count())) + 1,
               unsigned(values.getCapacity()));
  for (unsigned i = 0; i < size; ++i)
    s.rows.push_back({identity(values.getItems()[i]), 0});
  return s;
}
} // namespace

extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void *__wrap__Znam(std::size_t size) {
  if (!context.active)
    return __real__Znam(size);
  const unsigned kind = context.op < 2    ? context.attempts + 1
                        : context.op == 3 ? 1
                                          : 2;
  const bool success = ((context.fail >> context.attempts++) & 1) == 0;
  event(8, kind, unsigned(size), success);
  if (!success)
    return nullptr; // Explicit GCC -fcheck-new test allocator contract.
  void *p = __real__Znam(size);
  remember(p, kind, unsigned(size));
  return p;
}
extern "C" void __wrap__ZdaPv(void *p) {
  deleting(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t size) {
  deleting(p);
  __real__ZdaPvm(p, size);
}
extern "C" std::int64_t __real__ZN8presonus4dice19packetClockRawTicksEv();
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  if (!context.active)
    return __real__ZN8presonus4dice19packetClockRawTicksEv();
  ++context.clockCalls;
  event(1);
  return context.ticks;
}
extern "C" void
ctor1(Handler *) asm("_ZN8Presonus5Panel16ParamEditHandlerC1Ev");
extern "C" void
ctor2(Handler *) asm("_ZN8Presonus5Panel16ParamEditHandlerC2Ev");
extern "C" void
dtor1(Handler *) asm("_ZN8Presonus5Panel16ParamEditHandlerD1Ev");

namespace {
std::vector<unsigned char> replay(const unsigned char *input) {
  const unsigned op = word(input), arg = word(input + 4),
                 fail = word(input + 8), nE = word(input + 12),
                 nB = word(input + 16), editing = word(input + 20),
                 capE = word(input + 24), capB = word(input + 28);
  const auto ticks = static_cast<std::int64_t>(wide(input + 32));
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  std::strcpy(info.name, "fixture");
  info.maxValue = 1.;
  Param p1(info, 1), p2(info, 2), p3(info, 3);
  std::array<Param *, 4> params{nullptr, &p1, &p2, &p3};
  alignas(16) unsigned char keys[3][16]{};
  std::array<Presonus::Panel::Control *, 4> controls{
      nullptr, reinterpret_cast<Presonus::Panel::Control *>(keys[0]),
      reinterpret_cast<Presonus::Panel::Control *>(keys[1]),
      reinterpret_cast<Presonus::Panel::Control *>(keys[2])};
  Controller controller;
  for (unsigned i = 1; i < 4; ++i) {
    if ((editing >> (i - 1)) & 1)
      params[i]->Parameter::beginEdit();
    params[i]->setController(&controller);
  }
  alignas(Handler) unsigned char storage[sizeof(Handler)];
  auto *value = reinterpret_cast<Handler *>(storage);
  context.active = false;
  context.events.clear();
  context.allocations = {};
  context.op = op;
  context.fail = fail;
  context.attempts = 0;
  context.clockCalls = 0;
  context.ticks = ticks;
  if (op >= 2) {
    ctor1(value);
    auto &e = Access::edits(*value);
    auto &b = Access::blockers(*value);
    e.resize(int(capE));
    b.resize(int(capB));
    const auto *rows = input + 40;
    for (unsigned i = 0; i < nE; ++i, rows += 12)
      e.add({params.at(word(rows)), real(wide(rows + 4))});
    for (unsigned i = 0; i < nB; ++i, rows += 12)
      b.add({controls.at(word(rows)), real(wide(rows + 4))});
    remember(e.getItems(), 1, unsigned(e.getCapacity()) * 16);
    remember(b.getItems(), 2, unsigned(b.getCapacity()) * 16);
  }
  auto capture = [&](unsigned kind) {
    auto identify = [&](const auto &row) {
      if constexpr (std::is_same_v<std::decay_t<decltype(row)>,
                                   Handler::EditParam>) {
        for (unsigned i = 0; i < 4; ++i)
          if (row.parameter == params[i])
            return i;
      } else {
        for (unsigned i = 0; i < 4; ++i)
          if (row.control == controls[i])
            return i;
      }
      std::abort();
    };
    Snapshot result;
    if (kind == 0) {
      auto &items = Access::edits(*value);
      result = snapshot(items, nE, identify);
      for (unsigned i = 0; i < result.rows.size(); ++i)
        result.rows[i].time = bits(items.getItems()[i].lastEdit);
    } else {
      auto &items = Access::blockers(*value);
      result = snapshot(items, nB, identify);
      for (unsigned i = 0; i < result.rows.size(); ++i)
        result.rows[i].time = bits(items.getItems()[i].lastReceive);
    }
    return result;
  };
  Snapshot a, b;
  if (op == 2) {
    a = capture(0);
    b = capture(1);
  }
  context.active = true;
  unsigned result = 0;
  switch (op) {
  case 0:
    ctor1(value);
    break;
  case 1:
    ctor2(value);
    break;
  case 2:
    dtor1(value);
    break;
  case 3:
    value->handleParamEdit(params.at(arg));
    break;
  case 4:
    value->addReceiveBlocker(controls.at(arg));
    break;
  case 5:
    result = value->isReceiveBlocked(controls.at(arg));
    break;
  case 6:
    value->onIdle();
    break;
  default:
    std::abort();
  }
  context.active = false;
  if (op != 2) {
    a = capture(0);
    b = capture(1);
  }
  unsigned flags = 0;
  for (unsigned i = 1; i < 4; ++i)
    if (params[i]->Parameter::isEditing())
      flags |= 1 << (i - 1);
  std::vector<unsigned char> output;
  append(output, result, 4);
  for (auto n : a.header)
    append(output, n, 4);
  for (auto n : b.header)
    append(output, n, 4);
  for (auto n : {flags, context.clockCalls, unsigned(context.events.size()),
                 unsigned(a.rows.size()), unsigned(b.rows.size())})
    append(output, n, 4);
  for (auto *rows : {&a.rows, &b.rows})
    for (auto row : *rows) {
      append(output, row.identity, 4);
      append(output, row.time, 8);
    }
  for (auto item : context.events)
    for (auto n : item)
      append(output, n, 4);
  if (op != 2)
    dtor1(value);
  for (unsigned i = 1; i < 4; ++i)
    params[i]->setController(nullptr);
  return output;
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 2 && argc != 3)
    return 2;
  const bool normal = argc == 3 && std::strcmp(argv[2], "--normal") == 0;
  std::ifstream input(argv[1], std::ios::binary);
  std::vector<unsigned char> data((std::istreambuf_iterator<char>(input)), {});
  if (data.size() < 12 || std::memcmp(data.data(), "PEDTv001", 8))
    return 3;
  const unsigned count = word(data.data() + 8);
  std::size_t cursor = 12;
  unsigned matched = 0;
  for (unsigned i = 0; i < count; ++i) {
    if (cursor + 8 > data.size())
      return 4;
    const auto in = word(data.data() + cursor),
               expected = word(data.data() + cursor + 4);
    cursor += 8;
    if (cursor + in + expected > data.size())
      return 5;
    if (normal && word(data.data() + cursor + 8) != 0) {
      cursor += in + expected;
      continue;
    }
    auto actual = replay(data.data() + cursor);
    if (actual.size() != expected ||
        std::memcmp(actual.data(), data.data() + cursor + in, expected)) {
      std::fprintf(stderr, "case %u op %u mismatch sizes %zu/%u\n", i,
                   word(data.data() + cursor), actual.size(), expected);
      for (unsigned j = 0; j < std::min(actual.size(), std::size_t(expected));
           ++j)
        if (actual[j] != data[cursor + in + j]) {
          std::fprintf(stderr,
                       "first differing byte %u actual %u expected %u\n", j,
                       actual[j], data[cursor + in + j]);
          break;
        }
      return 6;
    }
    cursor += in + expected;
    ++matched;
  }
  if (cursor != data.size())
    return 7;
  std::printf("%u original ARM fixtures matched actual CCL/native helper, real "
              "allocation/deallocation/controller traces (%s)\n",
              matched,
              normal ? "ordinary allocator success"
                     : "explicit null-allocation seam");
}
