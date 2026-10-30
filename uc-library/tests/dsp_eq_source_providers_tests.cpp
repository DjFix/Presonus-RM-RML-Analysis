#ifdef NDEBUG
#undef NDEBUG
#endif
#include "core/public/coreformatter.h"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <limits>
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
Core::Interpolator *conflictFactory() { return new Core::LinearInterpolator; }
void mathContract() {
  using presonus::dsp::EqLogSourceInterpolator;
  EqLogSourceInterpolator log;
  rejects<std::domain_error>([&] { log.normalizedToRange(0.f); });
  rejects<std::domain_error>([&] { log.rangeToNormalized(36.f); });
  const float pairs[][2] = {{36, 465},   {90, 1200}, {380, 5000}, {1400, 18000},
                            {20, 20000}, {24, 1000}, {100, 20000}};
  double maximumNormalizedError = 0, maximumRelativeError = 0;
  unsigned samples = 0, domainRejections = 2;
  for (const auto &pair : pairs) {
    const float a = pair[0], b = pair[1];
    log.setRange(a, b, 0.f);
    assert(log.sourceRangeSupported());
    assert(log.normalizedToRange(0.f) == a && log.normalizedToRange(1.f) == b);
    assert(log.rangeToNormalized(a) == 0.f && log.rangeToNormalized(b) == 1.f);
    float previous = 0;
    for (unsigned i = 0; i <= 4096; ++i) {
      float n = static_cast<float>(i) / 4096.f;
      float value = log.normalizedToRange(n);
      assert(value >= a && value <= b && (i == 0 || value > previous));
      previous = value;
      long double expected =
          std::exp(std::log(static_cast<long double>(a)) +
                   static_cast<long double>(n) *
                       (std::log(static_cast<long double>(b)) -
                        std::log(static_cast<long double>(a))));
      double relative = static_cast<double>(
          std::fabs(static_cast<long double>(value) - expected) / expected);
      double inverse =
          std::fabs(static_cast<double>(log.rangeToNormalized(value)) - n);
      maximumRelativeError = std::max(maximumRelativeError, relative);
      maximumNormalizedError = std::max(maximumNormalizedError, inverse);
      assert(relative <= 3.e-6 && inverse <= 2.e-6);
      ++samples;
    }
    const float nearZero = std::nextafter(0.f, 1.f),
                nearOne = std::nextafter(1.f, 0.f);
    assert(log.normalizedToRange(nearZero) >= a &&
           log.normalizedToRange(nearZero) <=
               log.normalizedToRange(1.f / 4096.f));
    assert(log.normalizedToRange(nearOne) <= b &&
           log.normalizedToRange(nearOne) >=
               log.normalizedToRange(4095.f / 4096.f));
    for (float n : {std::nextafter(0.f, -1.f), std::nextafter(1.f, 2.f), -1.f,
                    2.f, std::numeric_limits<float>::infinity(),
                    std::numeric_limits<float>::quiet_NaN()}) {
      rejects<std::domain_error>([&] { log.normalizedToRange(n); });
      ++domainRejections;
    }
    for (float value :
         {std::nextafter(a, 0.f),
          std::nextafter(b, std::numeric_limits<float>::infinity()), 0.f, -1.f,
          std::numeric_limits<float>::infinity(),
          std::numeric_limits<float>::quiet_NaN()}) {
      rejects<std::domain_error>([&] { log.rangeToNormalized(value); });
      ++domainRejections;
    }
  }
  const float unsupported[][3] = {
      {0, 20000, 0},
      {-20, 20000, 0},
      {20, 20001, 0},
      {465, 36, 0},
      {36, 36, 0},
      {36, 465, 1},
      {36, 465, std::numeric_limits<float>::quiet_NaN()},
      {36, std::numeric_limits<float>::infinity(), 0}};
  for (const auto &p : unsupported) {
    rejects<std::invalid_argument>([&] { log.setRange(p[0], p[1], p[2]); });
    assert(!log.sourceRangeSupported());
    rejects<std::domain_error>([&] { log.normalizedToRange(.5f); });
    domainRejections += 2;
  }
  std::cout << "{\"math_passed\":true,\"ranges\":7,\"samples\":" << samples
            << ",\"domain_rejections\":" << domainRejections
            << ",\"maximum_normalized_error\":" << maximumNormalizedError
            << ",\"maximum_relative_error\":" << maximumRelativeError << "}\n";
}
void gateLogContract() {
  presonus::dsp::EqLogSourceInterpolator log;
  log.setRange(40.f, 16000.f, 0.f);
  float previous = 0.f;
  double maximumError = 0.;
  unsigned samples = 0, sentinelCases = 0, printCases = 0, rejections = 0;
  for (unsigned i = 0; i <= 4096; ++i) {
    const float n = static_cast<float>(i) / 4096.f;
    const float value = log.normalizedToRange(n);
    assert(value >= 40.f && value <= 16000.f && (!i || value > previous));
    previous = value;
    const long double expected =
        std::exp(std::log(40.L) + n * (std::log(16000.L) - std::log(40.L)));
    const auto error =
        std::fabs(static_cast<long double>(value) - expected) / expected;
    maximumError = std::max(maximumError, static_cast<double>(error));
    assert(error <= 3.e-6L);
    assert(std::fabs(log.rangeToNormalized(value) - n) <= 2.e-6f);
    ++samples;
  }
  const auto *formatter = Core::FormatterRegistry::find("freq/off");
  const auto *base = Core::FormatterRegistry::find("freq");
  assert(formatter && base && formatter != base);
  const Core::Formatter::Range range{40.f, 16000.f};
  const float threshold = 40.f + .01f;
  for (float value :
       {20.f, std::nextafter(20.f, 40.f), 21.f, 39.f,
        std::nextafter(40.f, 20.f), 40.f, std::nextafter(40.f, 16000.f),
        threshold, std::nextafter(threshold, 0.f),
        std::nextafter(threshold, 16000.f), 16000.f}) {
    const auto n = log.rangeToNormalized(value);
    assert(std::isfinite(n) && n >= 0.f && n <= 1.f);
    if (value <= 40.f) {
      assert(n == 0.f && log.normalizedToRange(n) == 40.f);
      ++sentinelCases;
    }
    char text[64]{}, expected[64]{};
    Core::Formatter::Data data{nullptr, text, 64, value, &range},
        other{nullptr, expected, 64, value, &range};
    formatter->print(data);
    if (value <= threshold)
      assert(std::strcmp(text, "off") == 0);
    else {
      base->print(other);
      assert(std::strcmp(text, expected) == 0);
    }
    ++printCases;
    data.range = nullptr;
    other.range = nullptr;
    formatter->print(data);
    base->print(other);
    assert(std::strcmp(text, expected) == 0);
    ++printCases;
  }
  for (float value : {std::nextafter(20.f, 0.f), 0.f, -0.f, -1.f,
                      std::nextafter(16000.f, 20000.f),
                      std::numeric_limits<float>::quiet_NaN(),
                      std::numeric_limits<float>::infinity(),
                      -std::numeric_limits<float>::infinity()}) {
    rejects<std::domain_error>([&] { log.rangeToNormalized(value); });
    ++rejections;
  }
  for (float n : {std::nextafter(0.f, -1.f), std::nextafter(1.f, 2.f),
                  std::numeric_limits<float>::quiet_NaN(),
                  std::numeric_limits<float>::infinity()}) {
    rejects<std::domain_error>([&] { log.normalizedToRange(n); });
    ++rejections;
  }
  // All retained seven domains still reject below-minimum inputs, even where
  // the new Gate sentinel20 itself lies below their minimum.
  for (const auto &pair : {std::pair<float, float>{36, 465},
                           {90, 1200},
                           {380, 5000},
                           {1400, 18000},
                           {20, 20000},
                           {24, 1000},
                           {100, 20000}}) {
    log.setRange(pair.first, pair.second, 0.f);
    rejects<std::domain_error>(
        [&] { log.rangeToNormalized(std::nextafter(pair.first, 0.f)); });
    ++rejections;
  }
  std::cout << "{\"gate_math_passed\":true,\"samples\":" << samples
            << ",\"sentinel_cases\":" << sentinelCases
            << ",\"print_cases\":" << printCases
            << ",\"domain_rejections\":" << rejections
            << ",\"maximum_relative_error\":" << maximumError
            << ",\"noninjective_default20_to0_to40\":true}\n";
}

void rangeFormatterContract() {
  const auto *base = Core::FormatterRegistry::find("freq.0");
  assert(base);
  unsigned prints = 0, scans = 0;
  for (const auto &config : {0, 1}) {
    const bool highPass = config == 0;
    const char *name = highPass ? "freq.0/off" : "freq.0/~/off";
    const auto *formatter = Core::FormatterRegistry::find(name);
    assert(formatter && formatter != base &&
           formatter == Core::FormatterRegistry::find(name));
    assert(std::strcmp(formatter->getName(), name) == 0);
    Core::Formatter::Range range{highPass ? 24.f : 100.f,
                                 highPass ? 1000.f : 20000.f};
    const float threshold =
        highPass ? range.minValue + .01f : range.maxValue - .01f;
    for (float value :
         {range.minValue, range.maxValue, threshold,
          std::nextafter(threshold, -std::numeric_limits<float>::infinity()),
          std::nextafter(threshold, std::numeric_limits<float>::infinity()),
          (range.minValue + range.maxValue) * .5f}) {
      char output[64]{}, expected[64]{};
      Core::Formatter::Data d{nullptr, output, 64, value, &range},
          b{nullptr, expected, 64, value, &range};
      formatter->print(d);
      const bool off = highPass ? value <= threshold : value >= threshold;
      if (off)
        assert(std::strcmp(output, "off") == 0);
      else {
        base->print(b);
        assert(std::strcmp(output, expected) == 0);
      }
      ++prints;
      d.range = nullptr;
      formatter->print(d);
      b.range = nullptr;
      base->print(b);
      assert(std::strcmp(output, expected) == 0);
      ++prints;
    }
    for (const char *text :
         {"off", "24", "100", "1000", "20k", "invalid", ""}) {
      char input[64]{}, copy[64]{};
      std::strcpy(input, text);
      std::strcpy(copy, text);
      Core::Formatter::Data d{nullptr, input, 64, -123.f, &range},
          b{nullptr, copy, 64, -123.f, &range};
      const bool a = formatter->scan(d), c = base->scan(b);
      assert(a == c && d.value == b.value);
      ++scans;
    }
  }
  std::cout << "{\"range_formatter_passed\":true,\"prints\":" << prints
            << ",\"scans\":" << scans << ",\"actual_core_owned_wrappers\":2}\n";
}
} // namespace
int main(int argc, char **argv) {
  const char *mode = argc > 1 ? argv[1] : "normal";
  assert(!presonus::dsp::eqSourcePortProvidersReady());
  const auto *beforeGain = Core::FormatterRegistry::find("gain");
  const auto *beforeFreq = Core::FormatterRegistry::find("freq");
  const auto *beforeIntegerFreq = Core::FormatterRegistry::find("freq.0");
  const auto *beforeQ = Core::FormatterRegistry::find("eqq");
  if (std::strcmp(mode, "formatter-conflict") == 0 ||
      std::strcmp(mode, "integer-frequency-conflict") == 0) {
    const bool integerConflict =
        std::strcmp(mode, "integer-frequency-conflict") == 0;
    Core::IntFormatter conflict(integerConflict ? "freq.0" : "gain");
    Core::FormatterRegistry::add(&conflict);
    rejects<std::logic_error>(
        [] { presonus::dsp::registerEqSourcePortProviders(); });
    assert(!presonus::dsp::eqSourcePortProvidersReady());
    assert(Core::FormatterRegistry::find(integerConflict ? "freq.0" : "gain") ==
               &conflict &&
           Core::FormatterRegistry::find("freq") == beforeFreq &&
           Core::FormatterRegistry::find("eqq") == beforeQ);
    assert(!std::unique_ptr<Core::Interpolator>(
        Core::InterpolatorFactory::create("log")));
    std::cout << "{\"passed\":true,\"conflict\":\"formatter\",\"no_partial_"
                 "registration\":true}\n";
    return 0;
  }
  if (std::strcmp(mode, "factory-conflict") == 0) {
    Core::InterpolatorFactory::add("skew", conflictFactory);
    rejects<std::logic_error>(
        [] { presonus::dsp::registerEqSourcePortProviders(); });
    assert(!presonus::dsp::eqSourcePortProvidersReady());
    assert(Core::FormatterRegistry::find("freq.0") == beforeIntegerFreq &&
           Core::FormatterRegistry::find("gain") == beforeGain &&
           Core::FormatterRegistry::find("freq") == beforeFreq &&
           Core::FormatterRegistry::find("eqq") == beforeQ);
    assert(!std::unique_ptr<Core::Interpolator>(
        Core::InterpolatorFactory::create("log")));
    std::cout << "{\"passed\":true,\"conflict\":\"factory\",\"no_partial_"
                 "registration\":true}\n";
    return 0;
  }
  mathContract();
  std::vector<std::thread> threads;
  for (int i = 0; i < 8; ++i)
    threads.emplace_back(
        [] { presonus::dsp::registerEqSourcePortProviders(); });
  for (auto &thread : threads)
    thread.join();
  assert(presonus::dsp::eqSourcePortProvidersReady());
  const auto *gain = Core::FormatterRegistry::find("gain");
  const auto *frequency = Core::FormatterRegistry::find("freq");
  const auto *integerFrequency = Core::FormatterRegistry::find("freq.0");
  assert(integerFrequency);
  const auto *q = Core::FormatterRegistry::find("eqq");
  assert(gain && frequency && q);
  for (const char *name : {"gain", "freq", "freq.0", "eqq"}) {
    const auto *formatter = Core::FormatterRegistry::find(name);
    assert(std::strcmp(formatter->getName(), name) == 0);
    char output[64]{};
    Core::Formatter::Data data{nullptr, output, 64, 1.f, nullptr};
    formatter->print(data);
    assert(output[0]);
  }
  rangeFormatterContract();
  gateLogContract();
  std::unique_ptr<Core::Interpolator> skew(
      Core::InterpolatorFactory::create("skew")),
      log(Core::InterpolatorFactory::create("log"));
  assert(skew && log);
  assert(std::strcmp(skew->getName(), "skew") == 0 &&
         std::strcmp(log->getName(), "log") == 0);
  skew->setRange(.1f, 4.f, .6f);
  log->setRange(36.f, 465.f, 0.f);
  assert(log->normalizedToRange(0.f) == 36 &&
         log->normalizedToRange(1.f) == 465);
  presonus::dsp::registerEqSourcePortProviders();
  assert(Core::FormatterRegistry::find("gain") == gain &&
         Core::FormatterRegistry::find("freq") == frequency &&
         Core::FormatterRegistry::find("eqq") == q);
  std::cout << "{\"passed\":true,\"explicit_bootstrap\":true,\"concurrent_"
               "calls\":8,\"registered_formatters\":4,\"registered_factories\":"
               "2,\"idempotent\":true}\n";
}
