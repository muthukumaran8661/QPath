import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/constants.dart';
import '../providers/route_provider.dart';

class JudgeDemoPanel extends ConsumerWidget {
  const JudgeDemoPanel({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routeNotifier = ref.read(routeProvider.notifier);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceDark,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(color: AppColors.quantumPurple.withOpacity(0.5), width: 2),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.quantumPurple.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.bolt, color: AppColors.quantumCyan, size: 20),
                  ),
                  const SizedBox(width: 12),
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'SIH Judge & Demo Console',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        'Inject real-time anomalies to test QPSO live rerouting',
                        style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.close, color: AppColors.textSecondary),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Action Grid
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 2.2,
            children: [
              _DemoButton(
                title: 'Inject Accident',
                subtitle: 'Multi-vehicle crash ahead',
                icon: Icons.car_crash,
                color: AppColors.error,
                onTap: () {
                  routeNotifier.triggerDemoIncident('accident');
                  Navigator.pop(context);
                  _showSnack(context, 'Accident injected! WebSocket will trigger quantum reroute.');
                },
              ),
              _DemoButton(
                title: 'Close Flyover',
                subtitle: 'Total road blockage',
                icon: Icons.block,
                color: AppColors.warning,
                onTap: () {
                  routeNotifier.triggerDemoIncident('closure');
                  Navigator.pop(context);
                  _showSnack(context, 'Road closure injected! Alternative path evaluating.');
                },
              ),
              _DemoButton(
                title: 'Monsoon Flooding',
                subtitle: 'Deep potholes & roughness',
                icon: Icons.water_drop,
                color: Colors.blueAccent,
                onTap: () {
                  routeNotifier.triggerDemoIncident('pothole_hazard');
                  Navigator.pop(context);
                  _showSnack(context, 'Waterlogging simulated! Rerouting to smoother expressway.');
                },
              ),
              _DemoButton(
                title: 'Traffic Surge',
                subtitle: '3.5x Congestion Spike',
                icon: Icons.traffic,
                color: Colors.orangeAccent,
                onTap: () {
                  routeNotifier.triggerDemoIncident('congestion');
                  Navigator.pop(context);
                  _showSnack(context, 'Congestion wave injected!');
                },
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Reset Button
          SizedBox(
            width: double.infinity,
            height: 46,
            child: OutlinedButton.icon(
              onPressed: () async {
                final api = ref.read(apiServiceProvider);
                await api.resetIncidents();
                routeNotifier.computeRoute();
                Navigator.pop(context);
                _showSnack(context, 'Road graph restored to base state.');
              },
              icon: const Icon(Icons.restore, color: AppColors.quantumCyan, size: 18),
              label: const Text(
                'RESTORE PRISTINE BASE GRAPH',
                style: TextStyle(
                  color: AppColors.quantumCyan,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  letterSpacing: 0.5,
                ),
              ),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: AppColors.quantumCyan.withOpacity(0.3)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showSnack(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.surfaceElevated,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}

class _DemoButton extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _DemoButton({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                    maxLines: 1,
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textSecondary,
                    ),
                    maxLines: 1,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
