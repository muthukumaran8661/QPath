import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/constants.dart';
import '../providers/route_provider.dart';
import '../providers/simulation_provider.dart';

class SimulatorScreen extends ConsumerWidget {
  const SimulatorScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final simState = ref.watch(simulationProvider);
    final simNotifier = ref.read(simulationProvider.notifier);
    final routeState = ref.watch(routeProvider);

    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      appBar: AppBar(
        title: const Text('What-If Scenario Simulator'),
        backgroundColor: AppColors.surfaceDark,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Banner
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppColors.quantumPurple.withOpacity(0.3), AppColors.surfaceElevated],
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.quantumPurple.withOpacity(0.4)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.science_rounded, color: AppColors.quantumCyan, size: 28),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Pre-Trip Traffic Stress Testing',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.white),
                        ),
                        Text(
                          'Simulate weather, peak-hour surges & sudden bottlenecks before you travel.',
                          style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Time of Day Slider
            const Text(
              'Departure Time of Day',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        _formatHour(simState.timeOfDayHours),
                        style: const TextStyle(
                          color: AppColors.quantumCyan,
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                      Text(
                        (simState.timeOfDayHours >= 8 && simState.timeOfDayHours <= 10.5) ||
                                (simState.timeOfDayHours >= 17 && simState.timeOfDayHours <= 20)
                            ? '🔴 PEAK RUSH HOUR'
                            : '🟢 NORMAL FLOW',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: (simState.timeOfDayHours >= 8 && simState.timeOfDayHours <= 10.5) ||
                                  (simState.timeOfDayHours >= 17 && simState.timeOfDayHours <= 20)
                              ? AppColors.error
                              : AppColors.success,
                        ),
                      ),
                    ],
                  ),
                  Slider(
                    value: simState.timeOfDayHours,
                    min: 0.0,
                    max: 23.5,
                    divisions: 47,
                    activeColor: AppColors.quantumCyan,
                    inactiveColor: Colors.white12,
                    onChanged: (val) => simNotifier.setTimeOfDay(val),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Weather Condition Selector
            const Text(
              'Weather Condition',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _WeatherOption(
                  label: 'Clear',
                  icon: Icons.wb_sunny_rounded,
                  isSelected: simState.weather == 'clear',
                  onTap: () => simNotifier.setWeather('clear'),
                ),
                const SizedBox(width: 8),
                _WeatherOption(
                  label: 'Monsoon Rain',
                  icon: Icons.water_drop_rounded,
                  isSelected: simState.weather == 'rain_monsoon',
                  onTap: () => simNotifier.setWeather('rain_monsoon'),
                ),
                const SizedBox(width: 8),
                _WeatherOption(
                  label: 'Dense Fog',
                  icon: Icons.cloud_rounded,
                  isSelected: simState.weather == 'fog',
                  onTap: () => simNotifier.setWeather('fog'),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Run Simulation Button
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: simState.isLoading
                    ? null
                    : () {
                        simNotifier.runSimulation(routeState.source, routeState.destination);
                      },
                icon: simState.isLoading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                      )
                    : const Icon(Icons.play_arrow_rounded, color: Colors.black, size: 22),
                label: Text(
                  simState.isLoading ? 'RUNNING QUANTUM SIMULATION...' : 'EXECUTE WHAT-IF SIMULATION',
                  style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.5),
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Simulation Results View
            if (simState.result != null) ...[
              const Text(
                'Simulation Prediction & Comparison',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white),
              ),
              const SizedBox(height: 10),

              // AI Recommendation Card
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.quantumCyan.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.psychology, color: AppColors.quantumCyan, size: 20),
                        SizedBox(width: 8),
                        Text(
                          'INFINITYCORE QUANTUM PREDICTION',
                          style: TextStyle(
                            color: AppColors.quantumCyan,
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      simState.result!.aiRecommendation,
                      style: const TextStyle(fontSize: 13, color: AppColors.textPrimary, height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Metrics comparison card
              Row(
                children: [
                  Expanded(
                    child: _SimMetricCard(
                      title: 'Standard Route in Jam',
                      time: simState.result!.stressedRouteStandard.metrics.totalTimeFormatted,
                      dist: simState.result!.stressedRouteStandard.metrics.totalDistanceFormatted,
                      isStressed: true,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _SimMetricCard(
                      title: 'QPSO Detour in Jam',
                      time: simState.result!.stressedRouteQpso.metrics.totalTimeFormatted,
                      dist: simState.result!.stressedRouteQpso.metrics.totalDistanceFormatted,
                      isQpso: true,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _formatHour(double h) {
    int hour = h.toInt();
    int min = ((h - hour) * 60).toInt();
    String period = hour >= 12 ? 'PM' : 'AM';
    int displayHour = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
    return '${displayHour.toString().padLeft(2, '0')}:${min.toString().padLeft(2, '0')} $period';
  }
}

class _WeatherOption extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _WeatherOption({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.quantumCyan.withOpacity(0.18) : AppColors.surfaceElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? AppColors.quantumCyan : Colors.white12,
              width: isSelected ? 1.5 : 1,
            ),
          ),
          child: Column(
            children: [
              Icon(icon, color: isSelected ? AppColors.quantumCyan : AppColors.textSecondary, size: 24),
              const SizedBox(height: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: isSelected ? Colors.white : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SimMetricCard extends StatelessWidget {
  final String title;
  final String time;
  final String dist;
  final bool isStressed;
  final bool isQpso;

  const _SimMetricCard({
    required this.title,
    required this.time,
    required this.dist,
    this.isStressed = false,
    this.isQpso = false,
  });

  @override
  Widget build(BuildContext context) {
    Color borderColor = isQpso ? AppColors.quantumCyan : (isStressed ? AppColors.error : Colors.white12);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: isQpso ? AppColors.quantumCyan : AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            time,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white),
          ),
          Text(
            dist,
            style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
