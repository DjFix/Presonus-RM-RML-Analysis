#include "core/public/coreformatter.h"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include "presonus/mixer_dsp/GateSourceProviders.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <thread>
#include <vector>
namespace {
template <class E, class F> void rejects(F f) {
  bool caught = false;
  try {
    f();
  } catch (const E &) {
    caught = true;
  }
  assert(caught);
}
Core::Interpolator *conflict() { return new Core::LinearInterpolator; }
void noRegistration() {
  assert(!presonus::dsp::gateSourcePortProvidersReady());
  assert(!Core::FormatterRegistry::find("onoff"));
  assert(!std::unique_ptr<Core::Interpolator>(
      Core::InterpolatorFactory::create("exp")));
  assert(!std::unique_ptr<Core::Interpolator>(
      Core::InterpolatorFactory::create("gaterange")));
}
} // namespace
int main(int argc, char **argv) {
  const char *scenario = argc > 1 ? argv[1] : "normal";
  if (std::strcmp(scenario, "invalid-labels") == 0) {
    for (const char *label : {static_cast<const char *>(nullptr),
                              "12345678901234567890123456789012", "\x80"}) {
      rejects<std::invalid_argument>([&] {
        presonus::dsp::registerGateSourcePortProviders(label, "Off");
      });
      rejects<std::invalid_argument>(
          [&] { presonus::dsp::registerGateSourcePortProviders("On", label); });
    }
    noRegistration();
    std::cout << "{\"passed\":true,\"no_partial_registration\":true,\"invalid_"
                 "labels\":6}\n";
    return 0;
  }
  if (std::strcmp(scenario, "without-eq") == 0) {
    rejects<std::logic_error>(
        [] { presonus::dsp::registerGateSourcePortProviders("On", "Off"); });
    noRegistration();
    std::cout << "{\"passed\":true,\"no_partial_registration\":true}\n";
    return 0;
  }
  presonus::dsp::registerEqSourcePortProviders();
  if (std::strcmp(scenario, "without-compressor") == 0) {
    rejects<std::logic_error>(
        [] { presonus::dsp::registerGateSourcePortProviders("On", "Off"); });
    noRegistration();
    std::cout << "{\"passed\":true,\"no_partial_registration\":true}\n";
    return 0;
  }
  presonus::dsp::registerCompressorSourcePortProviders();
  if (std::strcmp(scenario, "onoff-conflict") == 0) {
    Core::IntFormatter other("onoff");
    Core::FormatterRegistry::add(&other);
    rejects<std::logic_error>(
        [] { presonus::dsp::registerGateSourcePortProviders("On", "Off"); });
    assert(Core::FormatterRegistry::find("onoff") == &other);
    assert(!presonus::dsp::gateSourcePortProvidersReady());
    assert(!std::unique_ptr<Core::Interpolator>(
        Core::InterpolatorFactory::create("exp")));
    assert(!std::unique_ptr<Core::Interpolator>(
        Core::InterpolatorFactory::create("gaterange")));
    std::cout << "{\"passed\":true,\"no_partial_registration\":true}\n";
    return 0;
  }
  if (std::strcmp(scenario, "exp-conflict") == 0 ||
      std::strcmp(scenario, "gaterange-conflict") == 0) {
    const char *name =
        std::strcmp(scenario, "exp-conflict") == 0 ? "exp" : "gaterange";
    Core::InterpolatorFactory::add(name, conflict);
    rejects<std::logic_error>(
        [] { presonus::dsp::registerGateSourcePortProviders("On", "Off"); });
    assert(!presonus::dsp::gateSourcePortProvidersReady());
    assert(!Core::FormatterRegistry::find("onoff"));
    assert(std::unique_ptr<Core::Interpolator>(
        Core::InterpolatorFactory::create(name)));
    const char *other = std::strcmp(name, "exp") == 0 ? "gaterange" : "exp";
    assert(!std::unique_ptr<Core::Interpolator>(
        Core::InterpolatorFactory::create(other)));
    std::cout << "{\"passed\":true,\"no_partial_registration\":true}\n";
    return 0;
  }
  assert(std::strcmp(scenario, "normal") == 0);
  char on[] = "On", off[] = "Off";
  presonus::dsp::registerGateSourcePortProviders(on, off);
  on[0] = 'X';
  off[0] = 'Y'; // source provider copies caller labels into realCCL buffers
  std::vector<std::thread> threads;
  for (unsigned i = 0; i < 8; ++i)
    threads.emplace_back(
        [] { presonus::dsp::registerGateSourcePortProviders("On", "Off"); });
  for (auto &thread : threads)
    thread.join();
  assert(presonus::dsp::gateSourcePortProvidersReady());
  const auto *formatter = Core::FormatterRegistry::find("onoff");
  assert(formatter);
  char text[32]{};
  Core::Formatter::Data d{nullptr, text, 32, 1.f, nullptr};
  formatter->print(d);
  assert(std::strcmp(text, "On") == 0);
  d.value = 0.f;
  formatter->print(d);
  assert(std::strcmp(text, "Off") == 0);
  std::strcpy(text, "oN");
  assert(formatter->scan(d) && d.value == 1.f);
  std::strcpy(text, "oFf");
  assert(formatter->scan(d) && d.value == 0.f);
  rejects<std::logic_error>([] {
    presonus::dsp::registerGateSourcePortProviders("Enabled", "Disabled");
  });
  assert(Core::FormatterRegistry::find("onoff") == formatter);
  std::unique_ptr<Core::Interpolator> exp(
      Core::InterpolatorFactory::create("exp"));
  std::unique_ptr<Core::Interpolator> range(
      Core::InterpolatorFactory::create("gaterange"));
  assert(exp && range);
  assert(exp->getMinRange() == .00002f && exp->getMaxRange() == .5f &&
         exp->getMidRange() == .005f);
  assert(std::fabs(exp->normalizedToRange(0.f) - .00002f) < 2.e-9f);
  assert(std::fabs(exp->normalizedToRange(1.f) - .5f) < 2.e-6f);
  exp->setRange(.00002f, .5f, .005f);
  range->setRange(-84.f, 0.f, -21.f);
  assert(range->getMinRange() == -84.f && range->getMaxRange() == 0.f &&
         range->getMidRange() == 1.f);
  assert(range->normalizedToRange(.5f) == -21.f);
  unsigned samples = 0;
  for (unsigned i = 0; i <= 4096; ++i) {
    const float n = static_cast<float>(i) / 4096.f;
    const float x = exp->normalizedToRange(n), r = range->normalizedToRange(n);
    assert(std::isfinite(x) && std::isfinite(r));
    // Exact original-app math comparison is a separate retained2140-case test.
    assert(std::fabs(exp->rangeToNormalized(x) - n) < 3.e-6f);
    assert(std::fabs(range->rangeToNormalized(r) - n) < 3.e-6f);
    ++samples;
  }
  std::cout << "{\"passed\":true,\"explicit_bootstrap\":true,\"samples\":"
            << samples
            << ",\"concurrent_calls\":8,\"copied_actual_core_buffers\":true,"
               "\"idempotent\":true}\n";
}
