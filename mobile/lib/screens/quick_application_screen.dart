// Candidature envoyée hors de Tremplin, notée en quelques secondes sur le téléphone ; elle
// part au PC à la synchronisation suivante, comme une candidature saisie sur le PC.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../revision_state.dart';

class QuickApplicationScreen extends StatefulWidget {
  const QuickApplicationScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<QuickApplicationScreen> createState() => _QuickApplicationScreenState();
}

class _QuickApplicationScreenState extends State<QuickApplicationScreen> {
  final company = TextEditingController();
  final title = TextEditingController();
  final url = TextEditingController();
  final note = TextEditingController();
  DateTime appliedOn = DateTime.now();
  bool missingCompany = false;

  @override
  void dispose() {
    for (final vController in [company, title, url, note]) {
      vController.dispose();
    }
    super.dispose();
  }

  Future<void> pickDay() async {
    final vToday = DateTime.now();
    final vPicked = await showDatePicker(
      context: context,
      initialDate: appliedOn,
      firstDate: vToday.subtract(const Duration(days: 365)),
      lastDate: vToday,
    );

    if (vPicked != null) {
      setState(() => appliedOn = vPicked);
    }
  }

  Future<void> save() async {
    final vMessenger = ScaffoldMessenger.of(context);
    final vSaved = context.texts.quickSaved;
    final vAdded = await widget.state.addQuickApplication(
      pCompany: company.text,
      pTitle: title.text,
      pUrl: url.text,
      pNote: note.text,
      pAppliedAt: DateTime(appliedOn.year, appliedOn.month, appliedOn.day, 12),
    );

    if (!mounted) {
      return;
    }

    setState(() => missingCompany = !vAdded);

    if (vAdded) {
      for (final vController in [company, title, url, note]) {
        vController.clear();
      }
      vMessenger.showSnackBar(SnackBar(content: Text(vSaved)));
    }
  }

  String day(DateTime pDay) =>
      '${pDay.day.toString().padLeft(2, '0')}/${pDay.month.toString().padLeft(2, '0')}/${pDay.year}';

  @override
  Widget build(BuildContext context) {
    final vText = context.texts;
    final vPending = widget.state.pendingQuickApplications;

    final rScreen = Scaffold(
      appBar: AppBar(title: Text(vText.quickTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(vText.quickHelp),
          const SizedBox(height: 12),
          TextField(
            controller: company,
            textCapitalization: TextCapitalization.words,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(
              labelText: vText.quickCompany,
              errorText: missingCompany ? vText.quickCompanyMissing : null,
            ),
          ),
          TextField(
            controller: title,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(labelText: vText.quickJobTitle),
          ),
          TextField(
            controller: url,
            keyboardType: TextInputType.url,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(labelText: vText.quickLink),
          ),
          TextField(
            controller: note,
            maxLines: 3,
            decoration: InputDecoration(labelText: vText.quickNote),
          ),
          const SizedBox(height: 8),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.event_outlined),
            title: Text(vText.quickAppliedOn(day(appliedOn))),
            trailing: TextButton(onPressed: pickDay, child: Text(vText.quickChangeDay)),
          ),
          FilledButton.icon(
            onPressed: save,
            icon: const Icon(Icons.send_outlined),
            label: Text(vText.quickSave),
          ),
          if (vPending.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text(vText.quickPending(vPending.length),
                style: Theme.of(context).textTheme.titleSmall),
            for (final (vIndex, vItem) in vPending.indexed)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.cloud_upload_outlined),
                title: Text('${vItem['company']}'),
                subtitle: Text(
                  [
                    if ('${vItem['title']}'.isNotEmpty) '${vItem['title']}',
                    day(DateTime.parse('${vItem['applied_at']}')),
                  ].join(' · '),
                ),
                trailing: IconButton(
                  tooltip: vText.quickRemove,
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () async {
                    await widget.state.removeQuickApplication(vIndex);
                    setState(() {});
                  },
                ),
              ),
          ],
        ],
      ),
    );

    return rScreen;
  }
}
