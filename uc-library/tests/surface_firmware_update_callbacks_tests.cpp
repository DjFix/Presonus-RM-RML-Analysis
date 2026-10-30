#include "presonus/surface_update/FirmwareUpdateComponent.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <vector>
using namespace Core::Portable;
static const ParamInfo textInfo[] = {PARAM_STRING(1, "alert", 0),
                                     PARAM_STRING(2, "title", 0),
                                     PARAM_STRING(3, "message", 0)};
static const ParamInfo progressInfo =
    PARAM_FLOAT(4, "progress", -100, 100, 0, 0, 0, 0, 0, 0);
struct Progress final : NumericParam {
  std::vector<std::pair<std::uint32_t, bool>> calls;
  Progress() : NumericParam(progressInfo) {}
  void setValue(float value, bool edit) override {
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof bits);
    calls.emplace_back(bits, edit);
    NumericParam::setValue(value, edit);
  }
};
int main(int argc, char **argv) {
  std::ifstream input;
  if (argc == 2) {
    input.open(argv[1]);
    if (!input)
      return 2;
    std::cin.rdbuf(input.rdbuf());
  } else if (argc != 1)
    return 2;
  const char *strings[] = {"", "Firmware", "Updating panel: 50%", "initial"};
  unsigned method, mask, present, bits, a, b, c, x, y, z, count, value, edit;
  unsigned total = 0;
  while (std::cin >> method >> mask >> present >> bits >> a >> b >> c >> x >>
         y >> z >> count >> value >> edit) {
    std::vector<ParamInfo> infos;
    for (unsigned tag = 1; tag <= 3; ++tag)
      if (mask & (1u << (tag - 1)))
        infos.push_back(textInfo[tag - 1]);
    Progress progress;
    Presonus::Surface::FirmwareUpdateComponent component(
        presonus::surface_update::CallbackSourcePort{}, infos.data(),
        static_cast<int>(infos.size()), present ? &progress : nullptr);
    for (unsigned tag = 1; tag <= 3; ++tag)
      if (auto *parameter = component.countParameters()
                                ? component.getParameterByTag(tag)
                                : nullptr)
        parameter->fromString("initial");
    progress.calls.clear();
    float scalar;
    std::memcpy(&scalar, &bits, sizeof scalar);
    switch (method) {
    case 0:
      component.setText(strings[a], strings[b]);
      break;
    case 1:
      component.onProgress(strings[a], strings[b], scalar);
      break;
    case 2:
      component.dismissAlert();
      break;
    case 3:
      component.doAlert(strings[a], strings[b], strings[c]);
      break;
    default:
      assert(false);
    }
    unsigned expected[] = {x, y, z};
    for (unsigned tag = 1; tag <= 3; ++tag)
      if (auto *parameter = component.countParameters()
                                ? component.getParameterByTag(tag)
                                : nullptr) {
        auto *text = StringParam::cast(parameter);
        assert(text && std::strcmp(text->getText().str(),
                                   strings[expected[tag - 1]]) == 0);
      }
    assert(progress.calls.size() == count);
    if (count)
      assert(progress.calls[0].first == value &&
             progress.calls[0].second == bool(edit));
    ++total;
  }
  assert(total == 1920);
  std::cout << "PASS original_callback_cases=" << total << '\n';
}
