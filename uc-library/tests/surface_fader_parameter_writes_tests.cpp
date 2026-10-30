#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace {
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
float floating(std::uint32_t value) {
  float result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
Core::Portable::ParamInfo info(int tag) {
  Core::Portable::ParamInfo result{};
  result.type = Core::Portable::ParamInfo::kFloat;
  result.tag = tag;
  std::strncpy(result.name, "fader", sizeof(result.name) - 1);
  result.minValue = -0x1p31f;
  result.maxValue = 0x1p31f;
  return result;
}
struct Port final : Presonus::IPanelPort {
  std::vector<std::array<std::uint8_t, 4>> frames;
  std::vector<int> &order;
  int result = 0;
  explicit Port(std::vector<int> &events) : order(events) {}
  int readMsg(Uart_Msg_Type &) override {
    throw std::logic_error("no real IO in fixture");
  }
  int writeMsg(Uart_Msg_Type &message) override {
    order.push_back(3);
    frames.push_back(message.bytes);
    return result;
  }
};
// Test-only capture/forward subtype, not a production Core provider. Every
// setter forwards the real pinned NumericParam body, then applies the captured
// boundary reselection even when genuine CCL suppresses an unchanged float
// notification.
struct CapturedParameter final : Core::Portable::NumericParam {
  presonus::surface::PanelRegistrarCommandState &state;
  Presonus::IPanelPort *replacement = nullptr;
  std::vector<int> &order;
  unsigned setterCalls = 0;
  std::uint32_t setterBits = 0;
  bool setterEdit = true;
  CapturedParameter(const Core::Portable::ParamInfo &metadata,
                    presonus::surface::PanelRegistrarCommandState &s,
                    std::vector<int> &events)
      : NumericParam(metadata), state(s), order(events) {}
  void setValue(float value, bool edit = false) override {
    ++setterCalls;
    setterBits = bits(value);
    setterEdit = edit;
    order.push_back(1);
    NumericParam::setValue(value, edit);
    if (replacement)
      state.port = replacement;
    order.push_back(2);
  }
};
} // namespace
int main(int argc, char **argv) {
  assert(argc == 2);
  unsigned cases = 0;
  for (bool reverse : {false, true}) {
    const auto speedInfo = info(900), touchInfo = info(901);
    presonus::surface::PanelRegistrarCommandState state;
    std::vector<int> order;
    Port first(order), second(order);
    Core::Portable::ParamList parameters;
    auto *speed = new CapturedParameter(speedInfo, state, order);
    auto *touch = new CapturedParameter(touchInfo, state, order);
    parameters.add(reverse ? touch : speed);
    parameters.add(reverse ? speed : touch);
    Presonus::Surface::PanelRegistrar registrar(parameters, state);
    std::ifstream input(argv[1]);
    assert(input);
    int tag, delta, reselect, expected, changed;
    std::uint32_t initial, converted;
    while (input >> tag >> initial >> delta >> reselect >> expected >>
           changed >> converted) {
      auto *selected = tag == 900 ? speed : touch;
      auto *other = tag == 900 ? touch : speed;
      assert(tag == 900 || tag == 901);
      selected->setValueFast(floating(initial));
      other->setValueFast(-77.75f);
      speed->setterCalls = touch->setterCalls = 0;
      selected->replacement = reselect ? &second : nullptr;
      state.port = &first;
      first.frames.clear();
      second.frames.clear();
      order.clear();
      first.result = second.result = cases % 3 == 0 ? -1 : cases % 3;
      const int actual = tag == 900
                             ? registrar.bumpFaderSpeed(delta)
                             : registrar.bumpFaderTouchSensitivity(delta);
      assert(actual == expected);
      assert(selected->setterCalls == static_cast<unsigned>(changed));
      assert(other->setterCalls == 0 && other->getValue() == -77.75f);
      if (changed) {
        assert(selected->setterBits == converted && !selected->setterEdit);
        assert(bits(selected->getValue()) == converted);
        assert(order == std::vector<int>({1, 2, 3}));
        auto &chosen = reselect ? second : first;
        auto &unused = reselect ? first : second;
        assert(unused.frames.empty() && chosen.frames.size() == 1);
        const std::array<std::uint8_t, 4> frame{
            static_cast<std::uint8_t>(tag == 900 ? 'v' : 'H'),
            static_cast<std::uint8_t>(expected), 0, 0};
        assert(chosen.frames[0] == frame);
      } else {
        assert(bits(selected->getValue()) == initial);
        assert(first.frames.empty() && second.frames.empty() && order.empty());
      }
      ++cases;
    }
    assert(input.eof());
  }
  assert(cases == 8192);
  std::cout << "PASS 8192 fader bump cases: real CCL forwarding; borrowed port "
               "reload; prefix2 plus adapted zero tail\n";
}
