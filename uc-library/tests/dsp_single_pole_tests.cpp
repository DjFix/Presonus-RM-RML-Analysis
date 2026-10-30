#include "presonus/dsp/single_pole.hpp"
#include <cerrno>
#include <cfenv>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <gnu/libc-version.h>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#if defined(__SSE__)
#include <xmmintrin.h>
#endif

static_assert(sizeof(float) == sizeof(std::uint32_t));
static std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
static float value(std::uint32_t raw) {
  float result;
  std::memcpy(&result, &raw, sizeof(result));
  return result;
}
static unsigned capturedCalls = 0;
static std::uint32_t capturedArgument = 0, capturedResult = 0;
#ifndef PRESONUS_MEASURE_REAL
#define PRESONUS_MEASURE_REAL __real_expf
#define PRESONUS_MEASURE_WRAP __wrap_expf
#endif
extern "C" float PRESONUS_MEASURE_REAL(float);
extern "C" float PRESONUS_MEASURE_WRAP(float argument) {
  ++capturedCalls;
  capturedArgument = bits(argument);
  const float result = PRESONUS_MEASURE_REAL(argument);
  capturedResult = bits(result);
  return result;
}
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  if (std::fesetround(FE_TONEAREST) != 0 || std::fegetround() != FE_TONEAREST)
    return 2;
  std::feclearexcept(FE_ALL_EXCEPT);
  std::uint32_t mxcsr = 0;
#if defined(__SSE__)
  mxcsr = _mm_getcsr();
  if ((mxcsr & 0x8040U) != 0)
    return 2; // Neither FTZ nor DAZ belongs to this measured domain.
#endif
  Dl_info provider{};
  if (dladdr(reinterpret_cast<void *>(&PRESONUS_MEASURE_REAL), &provider) ==
          0 ||
      provider.dli_fname == nullptr)
    return 2;
  std::ifstream input(argv[1]);
  std::ofstream differences(argv[2]);
  if (!input || !differences)
    return 2;
  differences << "index original_address frequency_bits rate_bits "
                 "expected_argument actual_argument expected_result "
                 "actual_result ulp_distance\n";
  std::string line;
  unsigned cases = 0, argumentMismatches = 0, returnMismatches = 0;
  std::uint64_t maxUlp = 0;
  errno = 17;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    unsigned index, original;
    std::uint32_t frequency, rate, expectedArgument, expectedResult;
    row >> index >> original >> frequency >> rate >> expectedArgument >>
        expectedResult;
    if (!row)
      return 2;
    capturedCalls = 0;
    const auto actual =
        bits(presonus::dsp::singlePole(value(frequency), value(rate)));
    if (capturedCalls != 1 || actual != capturedResult)
      return 1;
    const bool argumentWrong = capturedArgument != expectedArgument;
    const bool returnWrong = actual != expectedResult;
    argumentMismatches += argumentWrong;
    returnMismatches += returnWrong;
    const std::uint64_t distance = actual > expectedResult
                                       ? std::uint64_t(actual) - expectedResult
                                       : std::uint64_t(expectedResult) - actual;
    if (distance > maxUlp)
      maxUlp = distance;
    if (argumentWrong || returnWrong)
      differences << index << ' ' << original << ' ' << frequency << ' ' << rate
                  << ' ' << expectedArgument << ' ' << capturedArgument << ' '
                  << expectedResult << ' ' << actual << ' ' << distance << '\n';
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 2;
  std::cout << "{\"measurement_completed\":true,\"cases\":" << cases
            << ",\"pre_expf_argument_bit_mismatches\":" << argumentMismatches
            << ",\"return_bit_mismatches\":" << returnMismatches
            << ",\"maximum_positive_result_ulp_distance\":" << maxUlp
            << ",\"pre_expf_argument_exact\":"
            << (argumentMismatches == 0 ? "true" : "false")
            << ",\"return_bits_exact\":"
            << (returnMismatches == 0 ? "true" : "false")
            << ",\"host_rounding_mode\":" << std::fegetround()
            << ",\"initial_mxcsr\":" << mxcsr
            << ",\"host_final_exception_flags_not_compared\":"
            << std::fetestexcept(FE_ALL_EXCEPT)
            << ",\"host_errno_not_compared\":" << errno
            << ",\"host_glibc_version\":" << std::quoted(gnu_get_libc_version())
            << ",\"math_provider_object\":" << std::quoted(provider.dli_fname)
#if defined(PRESONUS_DSP_GLIBC29_PRIVATE)
            << ",\"provider_kind\":\"private GNU glibc 2.9 source\""
#else
            << ",\"provider_kind\":\"forwarded host expf\""
#endif
            << "}\n";
  // A return mismatch is explicitly a failed exact return comparison, never a
  // tolerance pass. The measurement driver may retain rc3 as pending evidence.
  return argumentMismatches ? 1 : returnMismatches ? 3 : 0;
}
