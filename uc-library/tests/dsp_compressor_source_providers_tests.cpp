#include "core/public/coreformatter.h"
#include "core/public/coreinterpolator.h"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <thread>
#include <vector>
namespace {
template <class Exception, class F> void rejects(F function) {
  bool caught = false;
  try {
    function();
  } catch (const Exception &) {
    caught = true;
  }
  assert(caught);
}
Core::Interpolator *conflictingFactory() {
  return new Core::LinearInterpolator;
}
void actualContracts() {
  const auto *time = Core::FormatterRegistry::find("time");
  const auto *ratio = Core::FormatterRegistry::find("ratio");
  const auto *limit = Core::FormatterRegistry::find("ratio/~/limit");
  assert(time && ratio && limit && limit != ratio &&
         limit == Core::FormatterRegistry::find("ratio/~/limit"));
  Core::Formatter::Range range{1, 20};
  char text[128]{};
  Core::Formatter::Data d{nullptr, text, 128, 2.f, &range};
  ratio->print(d);
  assert(std::strcmp(text, "2.0:1") == 0);
  d.value = 20;
  limit->print(d);
  assert(std::strcmp(text, "limit") == 0);
  d.value = 1;
  limit->print(d);
  assert(std::strcmp(text, "1.0:1") == 0);
  for (float value : {19.98f, 19.99f, 20.f, 20.01f}) {
    char direct[128]{};
    Core::Formatter::Data base{nullptr, direct, 128, value, &range};
    d.value = value;
    limit->print(d);
    if (value >= range.maxValue - .01f)
      assert(std::strcmp(text, "limit") == 0);
    else {
      ratio->print(base);
      assert(std::strcmp(text, direct) == 0);
    }
  }
  char input[] = "limit", copy[] = "limit";
  Core::Formatter::Data wrapped{nullptr, input, 6, -123.f, &range},
      base{nullptr, copy, 6, -123.f, &range};
  assert(limit->scan(wrapped) == ratio->scan(base) &&
         wrapped.value == base.value);
  for (auto value : {.0002f, .02f, .15f}) {
    d.value = value;
    time->print(d);
    assert(std::strcmp(text, value == .0002f ? "0.20 ms"
                             : value == .02f ? "20.0 ms"
                                             : "150 ms") == 0);
  }
  char milliseconds[] = "20 ms", seconds[] = "0.15 s";
  d.string = milliseconds;
  assert(time->scan(d) && std::fabs(d.value - .02f) < 1.e-8f);
  d.string = seconds;
  assert(time->scan(d) && d.value == .15f);
  std::unique_ptr<Core::Interpolator> interp(
      Core::InterpolatorFactory::create("ratio"));
  assert(interp && std::strcmp(interp->getName(), "ratio") == 0);
  interp->setRange(1, 20, 2);
  assert(interp->getMinRange() == 1 && interp->getMaxRange() == 20 &&
         interp->getMidRange() == 2);
  float previous = 0;
  double maxError = 0;
  unsigned samples = 0;
  for (unsigned i = 0; i <= 4096; ++i) {
    float n = static_cast<float>(i) / 4096.f;
    float value = interp->normalizedToRange(n);
    assert(std::isfinite(value) && value >= 1.f && value <= 20.00002f &&
           (i == 0 || value > previous));
    previous = value;
    long double ideal = 1.L / (1.L - .95L * static_cast<long double>(n));
    double relative = static_cast<double>(
        std::fabs(static_cast<long double>(value) - ideal) / ideal);
    assert(relative < 2.e-6);
    maxError = std::max(maxError, relative);
    float back = interp->rangeToNormalized(value);
    assert(std::fabs(back - n) < 1.e-6f);
    ++samples;
  }
  std::cout << "{\"contracts_passed\":true,\"ratio_samples\":" << samples
            << ",\"maximum_relative_error\":" << maxError
            << ",\"real_core_owned_range_wrapper\":true,\"real_time_"
               "formatter\":true}\n";
}
} // namespace
int main(int argc, char **argv) {
  const char *scenario = argc > 1 ? argv[1] : "normal";
  assert(!presonus::dsp::compressorSourcePortProvidersReady());
  if (std::strcmp(scenario, "without-eq") == 0) {
    rejects<std::logic_error>(
        [] { presonus::dsp::registerCompressorSourcePortProviders(); });
    assert(!presonus::dsp::compressorSourcePortProvidersReady() &&
           !Core::FormatterRegistry::find("time") &&
           !Core::FormatterRegistry::find("ratio"));
    std::cout << "{\"passed\":true,\"precondition_enforced\":true,\"no_partial_"
                 "registration\":true}\n";
    return 0;
  }
  presonus::dsp::registerEqSourcePortProviders();
  if (std::strcmp(scenario, "normal") != 0) {
    const bool timeConflict = std::strcmp(scenario, "time-conflict") == 0,
               ratioConflict = std::strcmp(scenario, "ratio-conflict") == 0,
               rangeConflict = std::strcmp(scenario, "range-conflict") == 0,
               factoryConflict = std::strcmp(scenario, "factory-conflict") == 0;
    assert(timeConflict || ratioConflict || rangeConflict || factoryConflict);
    Core::IntFormatter conflict(timeConflict    ? "time"
                                : ratioConflict ? "ratio"
                                                : "ratio/~/limit");
    if (!factoryConflict)
      Core::FormatterRegistry::add(&conflict);
    else
      Core::InterpolatorFactory::add("ratio", conflictingFactory);
    rejects<std::logic_error>(
        [] { presonus::dsp::registerCompressorSourcePortProviders(); });
    assert(!presonus::dsp::compressorSourcePortProvidersReady());
    assert(Core::FormatterRegistry::find("time") ==
           (timeConflict ? &conflict : nullptr));
    assert(Core::FormatterRegistry::find("ratio") ==
           (ratioConflict ? &conflict : nullptr));
    if (!factoryConflict)
      assert(!std::unique_ptr<Core::Interpolator>(
          Core::InterpolatorFactory::create("ratio")));
    std::cout << "{\"passed\":true,\"no_partial_registration\":true}\n";
    return 0;
  }
  std::vector<std::thread> threads;
  for (unsigned i = 0; i < 8; ++i)
    threads.emplace_back(
        [] { presonus::dsp::registerCompressorSourcePortProviders(); });
  for (auto &thread : threads)
    thread.join();
  assert(presonus::dsp::compressorSourcePortProvidersReady());
  const auto *time = Core::FormatterRegistry::find("time");
  const auto *ratio = Core::FormatterRegistry::find("ratio");
  actualContracts();
  presonus::dsp::registerCompressorSourcePortProviders();
  assert(time == Core::FormatterRegistry::find("time") &&
         ratio == Core::FormatterRegistry::find("ratio"));
  std::cout << "{\"passed\":true,\"explicit_bootstrap\":true,\"idempotent\":"
               "true,\"concurrent_calls\":8}\n";
}
