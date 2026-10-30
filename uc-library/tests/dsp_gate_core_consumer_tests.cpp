#include "core/portable/coreparams.h"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
int main() {
  presonus::dsp::registerEqSourcePortProviders();
  // Independent actual CCL configuration, not an assertion that the app's
  // original ParamInfo/layout/type/flags equal Core::Portable::ParamInfo.
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.tag = 3;
  std::strcpy(info.name, "keyfilter");
  info.minValue = 40.f;
  info.maxValue = 16000.f;
  info.midValue = 0.f;
  info.defaultValue = 20.f;
  info.deltaValue = 1.f / 500.f;
  info.unitName = "freq/off";
  info.curveName = "log";
  Core::Portable::NumericParam parameter(info);
  char text[64]{};
  assert(parameter.getMin() == 40.f && parameter.getMax() == 16000.f);
  assert(parameter.getValue() == 20.f && parameter.getDefault() == 20.f);
  assert(parameter.getNormalized() == 0.f);
  parameter.toString(text, 64);
  assert(std::strcmp(text, "off") == 0);
  parameter.fromString("off");
  assert(parameter.getValue() == 20.f); // actual range formatter scan delegates
  parameter.setNormalized(0.f);
  assert(parameter.getValue() == 40.f && parameter.getDefault() == 20.f);
  parameter.toString(text, 64);
  assert(std::strcmp(text, "off") == 0);
  parameter.setValue(20.f);
  assert(parameter.getValue() == 40.f); // genuine CCL ParamInfo::makeValid
  parameter.setValue(100.f);
  parameter.resetValue();
  assert(parameter.getValue() == 40.f && parameter.getDefault() == 20.f);
  parameter.setValueFast(20.f); // explicitly documented actual CCL bypass API
  assert(parameter.getValue() == 20.f && parameter.getNormalized() == 0.f);
  std::cout
      << "{\"passed\":true,\"actual_core_numericparam\":true,"
         "\"constructor_raw20\":true,\"normalized0\":true,"
         "\"prints_off\":true,\"normalized_roundtrip40\":true,"
         "\"set_reset_clamp40\":true,\"default_metadata20_preserved\":true,"
         "\"original_core_behavior_claimed\":false}\n";
}
