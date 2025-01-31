#ifndef EXECUTE_H
#define EXECUTE_H
#include <bits/stdc++.h>
#include <sys/resource.h>
#include <unistd.h>
using namespace std;

void set_cpu_limit(int seconds = 2)
{
    struct rlimit rl;
    rl.rlim_cur = seconds;
    rl.rlim_max = seconds + 1;
    setrlimit(RLIMIT_CPU, &rl);
}

void get_usage(string filename)
{
    set_cpu_limit();
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    auto time_used = ru.ru_utime.tv_sec * 1000 + ru.ru_utime.tv_usec / 1000 + ru.ru_stime.tv_sec * 1000 + ru.ru_stime.tv_usec / 1000;
    auto memory_used = ru.ru_minflt * (sysconf(_SC_PAGESIZE) / 1024.0);
    filename = filename + "_result" + ".txt";
    ofstream file(filename, ios::app);
    file << time_used << "\n";
    file << memory_used << "\n";
}

#endif // EXECUTE_H
