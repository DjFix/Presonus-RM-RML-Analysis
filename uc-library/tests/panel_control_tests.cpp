#include "presonus/panel/control.hpp"
#include "presonus/panel/param_edit_handler.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>

using Control = Presonus::Panel::Control;
using Timer = Control::Timer;
using Access = presonus::panel::ControlAccess;
using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
using Event = std::array<unsigned, 4>;
namespace {
// Static initialization of the real product helper can allocate before main.
// This independent scalar has constant initialization; inactive wrappers never
// inspect the dynamically initialized fixture context.
bool observing = false;
bool recording = false;
unsigned paramDepth = 0;
struct Allocation {
  void *pointer{};
  unsigned kind{}, identity{}, capacity{};
};
struct Context {
  std::array<Control *, 4> controls{};
  std::array<Parameter *, 4> params{};
  std::array<Presonus::Panel::IPanelIO *, 4> ios{};
  std::array<Allocation, 256> allocations{};
  std::array<unsigned, 4> observerCounts{}, probes{};
  std::vector<Event> events;
  bool probing{};
  bool verifyEditExpired{};
  unsigned op{}, fail{}, attempts{}, nextId{};
  std::int64_t ticks{};
} context;
void emit(unsigned a, unsigned b = 0, unsigned c = 0, unsigned d = 0) {
  recording = true;
  context.events.push_back({a, b, c, d});
  recording = false;
}
template <class T>
unsigned identity(const std::array<T *, 4> &items, T *value) {
  for (unsigned i = 0; i < items.size(); ++i)
    if (items[i] == value)
      return i;
  std::abort();
}
unsigned owner(Control *value) { return identity(context.controls, value); }
unsigned parameter(Parameter *value) { return identity(context.params, value); }
void remember(void *pointer, unsigned kind, unsigned id,
              unsigned capacity = 0) {
  if (!pointer)
    return;
  for (auto &entry : context.allocations)
    if (!entry.pointer) {
      entry = {pointer, kind, id, capacity};
      return;
    }
  std::abort();
}
Allocation *find(void *pointer) {
  for (auto &entry : context.allocations)
    if (pointer && entry.pointer == pointer)
      return &entry;
  return nullptr;
}
void releasing(void *pointer) {
  if (!observing || recording || paramDepth || !pointer)
    return;
  if (pointer == context.controls[1]) {
    emit(8, 1);
    return;
  }
  if (auto *entry = find(pointer)) {
    if (entry->kind == 0)
      emit(7, entry->identity);
    else
      emit(10, entry->kind, entry->capacity);
    *entry = {};
  }
}
struct Derived : Control {
  using Control::Control;
  void paramChanged(Parameter *value, int message) override {
    const unsigned id = parameter(value);
    if (context.probing)
      ++context.probes[id];
    else if (observing)
      emit(4, owner(this), id, unsigned(message));
    Control::paramChanged(value, message);
  }
  void broadcastValue(int value) override {
    if (observing)
      emit(5, owner(this), 8, unsigned(value));
    Control::broadcastValue(value);
  }
  void transmit() override {
    if (observing)
      emit(5, owner(this), 9);
    Control::transmit();
  }
  void timerCallback(int tag) override {
    if (context.verifyEditExpired &&
        (context.params[1]->isEditing() ||
         presonus::panel::ParamEditHandlerAccess::edits(Access::paramEdits())
                 .count() != 0))
      std::abort();
    if (observing)
      emit(5, owner(this), 12, unsigned(tag));
    Control::timerCallback(tag);
  }
};
unsigned word(const unsigned char *p) {
  unsigned value;
  std::memcpy(&value, p, 4);
  return value;
}
std::uint64_t wide(const unsigned char *p) {
  std::uint64_t value;
  std::memcpy(&value, p, 8);
  return value;
}
std::int64_t signedWide(const unsigned char *p) {
  std::int64_t value;
  std::memcpy(&value, p, 8);
  return value;
}
float real(unsigned bits) {
  float value;
  std::memcpy(&value, &bits, 4);
  return value;
}
void append(std::vector<unsigned char> &out, std::uint64_t value,
            unsigned size) {
  for (unsigned i = 0; i < size; ++i)
    out.push_back(static_cast<unsigned char>(value >> (8 * i)));
}
std::array<unsigned, 6> snapshot(Control &value) {
  return {unsigned(Access::lastLevel(value)),
          parameter(Access::parameter(value)),
          parameter(Access::altParameter(value)),
          parameter(Access::tertiaryParameter(value)),
          identity(context.ios, Access::io(value)),
          unsigned(Access::tag(value))};
}
} // namespace

extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *pointer = __real__Znwm(size);
  if (observing && !recording && !paramDepth) {
    if (size != sizeof(Timer))
      std::abort();
    const unsigned id = context.nextId++;
    remember(pointer, 0, id);
    emit(6, id);
  }
  return pointer;
}
extern "C" void *__wrap__Znam(std::size_t size) {
  if (!observing || recording || paramDepth)
    return __real__Znam(size);
  if (size % sizeof(Timer *))
    std::abort();
  const unsigned capacity = unsigned(size / sizeof(Timer *));
  const unsigned kind = context.op == 27 ? 2 : 1;
  const bool success = ((context.fail >> context.attempts++) & 1) == 0;
  emit(9, kind, capacity, success);
  if (!success)
    return nullptr; // Only the separate GCC -fcheck-new test build permits
                    // this.
  void *pointer = __real__Znam(size);
  remember(pointer, kind, 0, capacity);
  return pointer;
}
extern "C" void __wrap__ZdlPv(void *p) {
  releasing(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  releasing(p);
  __real__ZdlPvm(p, size);
}
extern "C" void __wrap__ZdaPv(void *p) {
  releasing(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t size) {
  releasing(p);
  __real__ZdaPvm(p, size);
}
extern "C" void
__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *observer) {
  if (observing) {
    const auto id = parameter(p);
    emit(2, id, owner(static_cast<Control *>(observer)));
    ++context.observerCounts[id];
  }
  ++paramDepth;
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
      p, observer);
  --paramDepth;
}
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *observer) {
  if (observing) {
    const auto id = parameter(p);
    emit(3, id, owner(static_cast<Control *>(observer)));
    if (context.observerCounts[id])
      --context.observerCounts[id];
  }
  ++paramDepth;
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      p, observer);
  --paramDepth;
}
extern "C" std::int64_t __real__ZN8presonus4dice19packetClockRawTicksEv();
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  if (!observing)
    return __real__ZN8presonus4dice19packetClockRawTicksEv();
  emit(1);
  return context.ticks;
}
extern "C" void controlC1(Control *, int) asm("_ZN8Presonus5Panel7ControlC1Ei");
extern "C" void controlC2(Control *, int) asm("_ZN8Presonus5Panel7ControlC2Ei");
extern "C" void controlD1(Control *) asm("_ZN8Presonus5Panel7ControlD1Ev");
extern "C" void controlD2(Control *) asm("_ZN8Presonus5Panel7ControlD2Ev");
extern "C" void controlD0(Control *) asm("_ZN8Presonus5Panel7ControlD0Ev");
extern "C" void timerC1(Timer *, Control *, int,
                        float) asm("_ZN8Presonus5Panel7Control5TimerC1EPS1_if");
extern "C" void timerC2(Timer *, Control *, int,
                        float) asm("_ZN8Presonus5Panel7Control5TimerC2EPS1_if");
extern "C" void controlLifecycleEntry(Control *, unsigned);

namespace {
std::vector<unsigned char> replay(const unsigned char *input) {
  const unsigned op = word(input), arg = word(input + 4),
                 second = word(input + 8), duration = word(input + 12),
                 last = word(input + 16), primary = word(input + 20),
                 alt = word(input + 24), tertiary = word(input + 28),
                 io = word(input + 32), tag = word(input + 36),
                 fail = word(input + 40), capacity = word(input + 44),
                 delta = word(input + 48), timerCount = word(input + 52);
  observing = false;
  context.verifyEditExpired = false;
  context.events.clear();
  context.allocations = {};
  context.observerCounts = {};
  context.probes = {};
  context.op = op;
  context.fail = fail;
  context.attempts = 0;
  context.nextId = timerCount + 1;
  context.ticks = signedWide(input + 56);
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1.;
  std::strcpy(info.name, "Control fixture");
  Core::Portable::NumericParam p1(info), p2(info), p3(info);
  context.params = {nullptr, &p1, &p2, &p3};
  alignas(16) unsigned char ioKeys[3][16]{};
  context.ios = {nullptr,
                 reinterpret_cast<Presonus::Panel::IPanelIO *>(ioKeys[0]),
                 reinterpret_cast<Presonus::Panel::IPanelIO *>(ioKeys[1]),
                 reinterpret_cast<Presonus::Panel::IPanelIO *>(ioKeys[2])};
  Derived other2(2), other3(3);
  Control *value = op <= 4
                       ? static_cast<Control *>(__real__Znwm(sizeof(Control)))
                       : static_cast<Control *>(new Derived(int(tag)));
  context.controls = {nullptr, value, &other2, &other3};
  if (op >= 2 && op <= 4)
    controlC1(value, int(tag));
  if (op >= 2) {
    Access::lastLevel(*value) = int(last);
    Access::parameter(*value) = context.params.at(primary);
    Access::altParameter(*value) = context.params.at(alt);
    Access::tertiaryParameter(*value) = context.params.at(tertiary);
    Access::io(*value) = context.ios.at(io);
    Access::tag(*value) = int(tag);
    for (auto id : {primary, alt, tertiary})
      if (id) {
        context.params[id]->addObserver(value);
        ++context.observerCounts[id];
      }
  }
  auto &queue = Access::timers();
  if (queue.count())
    std::abort();
  queue.setDelta(int(delta));
  if (!queue.resize(int(capacity)))
    std::abort();
  for (int i = 0; i < queue.getCapacity(); ++i)
    queue.getItems()[i] = nullptr;
  const auto *rows = input + 64;
  for (unsigned i = 0; i < timerCount; ++i, rows += 16) {
    auto *timer =
        new Timer(context.controls.at(word(rows)), int(word(rows + 4)), 0.f);
    timer->deadline = signedWide(rows + 8);
    remember(timer, 0, i + 1);
    queue.add(timer);
  }
  remember(queue.getItems(), 1, 0, unsigned(queue.getCapacity()));
  alignas(Timer) unsigned char timerStorage[sizeof(Timer)];
  auto *standalone = reinterpret_cast<Timer *>(timerStorage);
  if (op == 7) {
    timerC1(standalone, context.controls.at(arg), int(second), 0.f);
    standalone->deadline = 0;
  }
  std::array<unsigned, 6> state{};
  if (op >= 2 && op <= 4)
    state = snapshot(*value); // Never inspect an ended Control lifetime later.
  if (op >= 2 && op <= 4) {
    auto **table = *reinterpret_cast<void ***>(value);
    if (table[2] != reinterpret_cast<void *>(&controlD1) ||
        table[3] != reinterpret_cast<void *>(&controlD0))
      std::abort();
  }
  observing = true;
  unsigned result = 0;
  switch (op) {
  case 0:
    controlC1(value, int(arg));
    break;
  case 1:
    controlC2(value, int(arg));
    break;
  case 2:
    controlLifecycleEntry(value, 2);
    break;
  case 3:
    controlD2(value);
    break;
  case 4:
    controlLifecycleEntry(value, 3);
    break;
  case 5:
    timerC1(standalone, context.controls.at(arg), int(second), real(duration));
    break;
  case 6:
    timerC2(standalone, context.controls.at(arg), int(second), real(duration));
    break;
  case 7:
    standalone->notify();
    break;
  case 8:
    result = parameter(value->Control::getParameter());
    break;
  case 9:
    result = parameter(value->Control::getAltParameter());
    break;
  case 10:
    result = parameter(value->Control::getTertiaryParameter());
    break;
  case 11:
    value->Control::setIO(context.ios.at(arg));
    break;
  case 12:
    result = value->Control::castTo(int(arg)) == value ? 1 : 0;
    break;
  case 13:
    result = unsigned(value->Control::getParameterMode());
    break;
  case 14:
    value->Control::broadcastValue(int(arg));
    break;
  case 15:
    value->Control::transmit();
    break;
  case 16:
    value->Control::disableControl(bool(arg), bool(second));
    break;
  case 17:
    value->Control::receiveValue(int(arg));
    break;
  case 18:
    value->Control::timerCallback(int(arg));
    break;
  case 19:
    value->Control::resendLastLevel();
    break;
  case 20:
    result = value->Control::setParameter(context.params.at(arg), int(second));
    break;
  case 21:
    result = value->Control::setAltParameter(context.params.at(arg));
    break;
  case 22:
    result = value->Control::setTertiaryParameter(context.params.at(arg));
    break;
  case 23:
    value->Control::paramChanged(context.params.at(arg), int(second));
    break;
  case 24:
    value->Control::startTimer(real(duration), int(arg));
    break;
  case 25:
    value->Control::stopTimer(int(arg));
    break;
  case 26:
    result = value->Control::isTimerRunning(int(arg));
    break;
  case 27:
    Control::onIdle();
    break;
  default:
    std::abort();
  }
  observing = false;
  if (!(op >= 2 && op <= 4))
    state = snapshot(*value);
  // Probe the actual CCL observer list in ordinary live-Derived domains.
  // Lifecycle domains rely on the real add/remove API call traces; no virtual
  // callback into an ended object is attempted.
  if (op > 4) {
    context.probing = true;
    for (unsigned i = 1; i < 4; ++i)
      context.params[i]->changed();
    context.probing = false;
    if (context.probes != context.observerCounts)
      std::abort();
  }
  std::vector<Allocation> live;
  for (auto entry : context.allocations)
    if (entry.pointer && entry.kind == 0)
      live.push_back(entry);
  std::sort(live.begin(), live.end(),
            [](auto a, auto b) { return a.identity < b.identity; });
  std::array<unsigned, 4> timer{};
  if (op >= 5 && op <= 7) {
    const auto time = static_cast<std::uint64_t>(standalone->deadline);
    timer = {owner(standalone->control), unsigned(standalone->tag),
             unsigned(time), unsigned(time >> 32)};
  }
  std::vector<unsigned char> output;
  append(output, result, 4);
  for (auto n : state)
    append(output, n, 4);
  for (auto n : {unsigned(queue.count()), unsigned(queue.getCapacity()),
                 unsigned(queue.getDelta()),
                 unsigned(queue.getItems() != nullptr), unsigned(live.size()),
                 unsigned(context.events.size()), context.observerCounts[1],
                 context.observerCounts[2], context.observerCounts[3]})
    append(output, n, 4);
  for (auto n : timer)
    append(output, n, 4);
  for (int i = 0; i < queue.count(); ++i) {
    const auto *entry = find(queue.at(i));
    if (!entry)
      std::abort();
    append(output, entry->identity, 4);
  }
  for (auto entry : live) {
    auto *value = static_cast<Timer *>(entry.pointer);
    append(output, entry.identity, 4);
    append(output, owner(value->control), 4);
    append(output, unsigned(value->tag), 4);
    append(output, static_cast<std::uint64_t>(value->deadline), 8);
  }
  for (auto event : context.events)
    for (auto n : event)
      append(output, n, 4);
  // Fixture cleanup also owns otherwise orphaned timers, after observation.
  queue.removeAll();
  for (auto entry : live)
    delete static_cast<Timer *>(entry.pointer);
  if (op == 2 || op == 3)
    __real__ZdlPv(value);
  else if (op != 4)
    delete value;
  return output;
}

void composition() {
  observing = false;
  context.events.clear();
  context.allocations = {};
  context.observerCounts = {};
  context.probes = {};
  context.op = 27;
  context.fail = 0;
  context.attempts = 0;
  context.nextId = 2;
  context.ticks = 0;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1.;
  std::strcpy(info.name, "Composed edit");
  Core::Portable::NumericParam parameter(info);
  Derived control(77);
  context.params = {nullptr, &parameter, nullptr, nullptr};
  context.controls = {nullptr, &control, nullptr, nullptr};
  auto &handler = Access::paramEdits();
  if (presonus::panel::ParamEditHandlerAccess::edits(handler).count() ||
      presonus::panel::ParamEditHandlerAccess::blockers(handler).count())
    std::abort();
  observing = true;
  handler.handleParamEdit(&parameter);
  observing = false;
  if (!parameter.isEditing() ||
      presonus::panel::ParamEditHandlerAccess::edits(handler).count() != 1)
    std::abort();
  auto &queue = Access::timers();
  if (queue.count())
    std::abort();
  queue.setDelta(5);
  queue.resize(5);
  auto *timer = new Timer(&control, 99, 0.f);
  timer->deadline = 1000;
  queue.add(timer);
  remember(queue.getItems(), 1, 0, unsigned(queue.getCapacity()));
  remember(timer, 0, 1);
  context.ticks = 1000000001;
  context.verifyEditExpired = true;
  observing = true;
  Control::onIdle();
  observing = false;
  context.verifyEditExpired = false;
  if (parameter.isEditing() || queue.count() ||
      presonus::panel::ParamEditHandlerAccess::edits(handler).count())
    std::abort();
  unsigned callbacks = 0;
  for (const auto &event : context.events)
    if (event == Event{5, 1, 12, 99})
      ++callbacks;
  if (callbacks != 1)
    std::abort();
  std::puts("COMPOSED actual ParamEditHandler expiry precedes Control timer "
            "callback PASS");
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2 && argc != 3)
    return 2;
  const bool normal = argc == 3 && std::strcmp(argv[2], "--normal") == 0;
  std::ifstream input(argv[1], std::ios::binary);
  std::vector<unsigned char> data((std::istreambuf_iterator<char>(input)), {});
  if (data.size() < 12 || std::memcmp(data.data(), "CTRLv001", 8))
    return 3;
  const auto count = word(data.data() + 8);
  std::size_t cursor = 12;
  unsigned matched = 0;
  for (unsigned i = 0; i < count; ++i) {
    if (cursor + 8 > data.size())
      return 4;
    const auto size = word(data.data() + cursor),
               expected = word(data.data() + cursor + 4);
    cursor += 8;
    if (cursor + size + expected > data.size())
      return 5;
    if (normal && word(data.data() + cursor + 40)) {
      cursor += size + expected;
      continue;
    }
    auto actual = replay(data.data() + cursor);
    if (actual.size() != expected ||
        std::memcmp(actual.data(), data.data() + cursor + size, expected)) {
      std::fprintf(stderr, "case %u op %u mismatch size %zu/%u\n", i,
                   word(data.data() + cursor), actual.size(), expected);
      for (unsigned j = 0; j < std::min(actual.size(), std::size_t(expected));
           ++j)
        if (actual[j] != data[cursor + size + j]) {
          std::fprintf(stderr, "first byte %u actual %u expected %u\n", j,
                       actual[j], data[cursor + size + j]);
          break;
        }
      return 6;
    }
    cursor += size + expected;
    ++matched;
  }
  if (cursor != data.size())
    return 7;
  composition();
  std::printf(
      "PASS %u original Control fixtures (%s); actual CCL, actual native D1/D0 "
      "table entries, Timer size%zu and native pointer size%zu\n",
      matched, normal ? "ordinary allocation" : "null-array seam",
      sizeof(Timer), sizeof(Timer *));
}
