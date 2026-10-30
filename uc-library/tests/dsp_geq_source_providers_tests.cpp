#include "core/public/coreformatter.h"
#include "core/public/coreinterpolator.h"
#include "presonus/mixer_dsp/GEQSourceProviders.hpp"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <thread>
#include <vector>
int main(int argc, char **argv) {
  assert(!presonus::dsp::geqSourcePortProvidersReady());
  Core::FormatterRegistry::find("");
  if (argc > 1 && std::strcmp(argv[1], "conflict") == 0) {
    Core::IntFormatter other("gain.1.value");
    Core::FormatterRegistry::add(&other);
    bool caught = false;
    try {
      presonus::dsp::registerGEQSourcePortProviders();
    } catch (const std::logic_error &) {
      caught = true;
    }
    assert(caught && !presonus::dsp::geqSourcePortProvidersReady());
    assert(Core::FormatterRegistry::find("gain.1.value") == &other);
    std::cout << "{\"passed\":true,\"no_partial_registration\":true}\n";
    return 0;
  }
  std::vector<std::thread> threads;
  for (unsigned i = 0; i < 8; ++i)
    threads.emplace_back(
        [] { presonus::dsp::registerGEQSourcePortProviders(); });
  for (auto &t : threads)
    t.join();
  assert(presonus::dsp::geqSourcePortProvidersReady());
  auto *formatter = Core::FormatterRegistry::find("gain.1.value");
  assert(formatter);
  presonus::dsp::registerGEQSourcePortProviders();
  assert(Core::FormatterRegistry::find("gain.1.value") == formatter);
  std::unique_ptr<Core::Interpolator> curve(
      Core::InterpolatorFactory::create("linear"));
  assert(curve);
  curve->setRange(-12.f, 12.f, 0.f);
  for (unsigned i = 0; i <= 4096; ++i) {
    float n = static_cast<float>(i) / 4096.f;
    float value = curve->normalizedToRange(n);
    assert(value >= -12.f && value <= 12.f &&
           curve->rangeToNormalized(value) == n);
    char text[64]{}, expected[64]{};
    Core::Formatter::Data data{nullptr, text, sizeof text, value, nullptr};
    formatter->print(data);
    std::snprintf(expected, sizeof expected, "%.1f",
                  static_cast<double>(value));
    assert(std::strcmp(text, expected) == 0);
    assert(formatter->scan(data));
    assert(std::fabs(data.value - value) <= 0.051f);
  }
  char invalid[] = "invalid";
  Core::Formatter::Data data{nullptr, invalid, sizeof invalid, 71.f, nullptr};
  assert(!formatter->scan(data));
  std::cout << "{\"passed\":true,\"samples\":4097,\"concurrent_calls\":8,"
               "\"idempotent\":true}\n";
}
