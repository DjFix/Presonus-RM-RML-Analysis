#include "presonus/dsp/ControllerProperties.hpp"
#include "presonus/mixer_dsp/EQ4Controller.hpp"
#include "presonus/mixer_dsp/EqParameterLists.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string_view>

namespace {
void *watchedReceiver;
void *watchedBands;
bool receiverFreed;
bool bandsFreed;
} // namespace

void *operator new(std::size_t size) {
  if (auto *p = std::malloc(size ? size : 1))
    return p;
  throw std::bad_alloc{};
}

void operator delete(void *p) noexcept {
  if (watchedReceiver && p == watchedReceiver)
    receiverFreed = true;
  if (watchedBands && p == watchedBands)
    bandsFreed = true;
  std::free(p);
}

void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }

namespace {
using namespace Presonus::Dsp;

struct Recipient : Core::IPropertyHandler {
  void setProperty(const Core::Property &p) override {
    if (p.type != EQ4CoefficientsProperty::kID ||
        p.size != sizeof(EQ4CoefficientsProperty))
      throw std::runtime_error("unexpected property");
    const auto &eq = static_cast<const EQ4CoefficientsProperty &>(p);
    ++sent;
    payload[0] = static_cast<std::uint32_t>(p.type);
    payload[1] = static_cast<std::uint32_t>(p.size);
    payload[2] = std::bit_cast<std::uint32_t>(eq.channel);
    payload[3] = std::bit_cast<std::uint32_t>(eq.gain);
    const auto tables = {&eq.firstNumerator, &eq.secondNumerator,
                         &eq.firstFeedback, &eq.secondFeedback};
    unsigned i = 4;
    for (const auto *table : tables)
      for (float value : *table)
        payload[i++] = std::bit_cast<std::uint32_t>(value);
  }
  void getProperty(Core::Property &) override {}
  void release() override {
    if (receiverFreed)
      throw std::runtime_error("owned target released after storage disposal");
    ++released;
  }
  std::array<std::uint32_t, 20> payload{};
  unsigned sent = 0, released = 0;
};

using std::cout;
void emit(auto v) { cout << +v << ' '; }
std::uint32_t bits(float v) { return std::bit_cast<std::uint32_t>(v); }

struct EQ4Derived : EQ4Controller {
  explicit EQ4Derived(int id) : EQ4Controller(id) {}
};

void describe(const EQ4Controller &eq) {
  const auto &s = eq.sourceState();
  if (s.descriptorList !=
          &presonus::dsp::sourceList(*EqParamList::instance()) ||
      eq.getNumParameters() != 25 || eq.getNumBands() != 4)
    throw std::runtime_error("unexpected provider descriptor or band count");
  emit(s.word08);
  emit(static_cast<std::uint32_t>(s.constructorId));
  emit(s.processDirty);
  emit(eq.getValue(0) != 0.f);
  for (const auto &band : eq.portableBands()) {
    emit(band.type);
    emit(bits(band.frequency));
    emit(bits(band.q));
    emit(bits(band.gain));
    emit(band.edgeSelectable);
    emit(band.dirty);
    emit(band.enabled);
    emit(band.calculator.portableState().byte48);
  }
  cout << '\n';
}

void destroy(int id, bool deleting) {
  Recipient recipient;
  void *storage = ::operator new(sizeof(EQ4Controller));
  auto *eq = new (storage) EQ4Controller(id);
  watchedReceiver = storage;
  watchedBands = eq->portableBands().data();
  receiverFreed = bandsFreed = false;
  eq->setTarget(&recipient);
  eq->makeTargetOwner();
  if (deleting) {
    Controller *base = eq;
    delete base;
  } else {
    eq->~EQ4Controller();
  }
  emit(recipient.released);
  emit(receiverFreed);
  emit(bandsFreed);
  cout << '\n';
  watchedReceiver = watchedBands = nullptr;
  if (!deleting)
    ::operator delete(storage);
}

void update() {
  int throughFlush, enabled, mask, dirty, processDirty, target;
  float rate;
  while (std::cin >> throughFlush >> enabled >> mask >> dirty >> processDirty >>
         target >> rate) {
    EQ4Controller eq(9);
    SetupProperty setup;
    setup.rate = 48000.f;
    eq.setupProcess(setup);
    Recipient recipient;
    auto &state = eq.sourceState();
    state.word04 = std::bit_cast<std::uint32_t>(-49);
    eq.setTarget(target ? &recipient : nullptr);
    state.processDirty = processDirty;
    state.processRateBits = bits(rate);
    eq.portableEnabled() = enabled;
    for (unsigned i = 0; i < 4; ++i) {
      auto &band = eq.portableBands()[i];
      band.type = 6;
      band.frequency = 1000.f + 250.f * i;
      band.q = .75f + .125f * i;
      band.gain = 3.f + i;
      band.dirty = (dirty >> i) & 1;
      band.enabled = (mask >> i) & 1;
      auto &coefficients = const_cast<presonus::dsp::BiquadState<double> &>(
                               band.calculator.portableState())
                               .coefficients;
      const double n = i;
      const std::array<double, 5> initial = {2. + n, -3. - n, .5 + n, -.125 - n,
                                             4. + n};
      for (unsigned j = 0; j < 5; ++j)
        coefficients[j] = initial[j];
    }
    int result = -1;
    if (throughFlush)
      result = static_cast<int>(eq.flushParameterChanges());
    else
      eq.doUpdates();
    emit(result);
    emit(state.processDirty);
    for (const auto &band : eq.portableBands())
      emit(band.dirty);
    emit(recipient.sent);
    if (recipient.sent)
      for (auto v : recipient.payload)
        emit(v);
    for (const auto &band : eq.portableBands())
      for (auto c : band.calculator.portableState().coefficients)
        emit(std::bit_cast<std::uint64_t>(c));
    cout << '\n';
  }
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string_view task = argv[1];
  if (task == "do_updates") {
    update();
    return 0;
  }
  int id;
  while (std::cin >> id) {
    if (task == "complete_construct") {
      EQ4Controller eq(id);
      describe(eq);
    } else if (task == "base_construct") {
      EQ4Derived eq(id);
      describe(eq);
    } else if (task == "complete_destroy" || task == "deleting_destroy") {
      destroy(id, task == "deleting_destroy");
    } else {
      return 2;
    }
  }
}
