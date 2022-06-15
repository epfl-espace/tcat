from Commons.common import *
from Commons.plotting import *
from Modules.PropulsionModule import PropulsionModule

#DEPRECATED
client_str = 'OneWeb'

# architecture_str = 'refueled_shuttle_high'
# load data as scenarios['number of tgts per servicer']['number of servicers']
# architectures = [load_latest_file('Results', client_str + '_' + architecture_str + '_chemical'),
#                  load_latest_file('Results', client_str + '_' + architecture_str + '_electrical'),
#                  load_latest_file('Results', client_str + '_' + architecture_str + '_water')
#                  ]

architectures = [load_latest_file('Results', client_str + '_' + 'refueled_shuttle_high' + '_chemical')
                 ]

# # results
for architecture in architectures:
    for tgt_per_servicer, scenarios in architecture.items():
        for number_of_servicers, scenario in scenarios.items():
            fig, ax = plt.subplots(3, figsize=(20, 10))

            plot_servicer_mass_summary(architecture, first_parameters=[tgt_per_servicer],
                                       second_parameters=[number_of_servicers],  rm_duplicates=True,
                                       offset_text=-5, text_limit=20, ax=ax[0], fig=fig)

            plot_cost_summary(architecture, first_parameters=[tgt_per_servicer],
                              second_parameters=[number_of_servicers], offset_text=-0.5,
                              text_limit=2, ax=ax[1], fig=fig)

            plot_servicer_cost_summary(architecture, first_parameters=[tgt_per_servicer],
                                       second_parameters=[number_of_servicers], rm_duplicates=True,
                                       offset_text=-20, text_limit=1, ax=ax[2], fig=fig)

            plt.subplots_adjust(left=0.05, bottom=0.05, right=0.8, top=0.9, wspace=0.5, hspace=0.5)
            fig.suptitle(str(number_of_servicers) + 'x' + str(tgt_per_servicer) + ' ' + scenario.architecture
                         + ' ' + scenario.prop_type + ' ' + scenario.clients.ID + ' - Cost per removal : '
                         + "{:.1f}".format(scenario.get_cost_per_target(with_development=False).value / 1000000)
                         + ' MEuros', fontsize=18)
            plt.savefig(str(number_of_servicers) + 'x' + str(tgt_per_servicer)
                        + '_' + scenario.architecture + '_' + scenario.prop_type + '_' + scenario.clients.ID)
            plt.show()

#
# shuttle_scenario = architectures[0]['6']['1']
#
# print(shuttle_scenario.fleet.servicers['servicer0000'].get_dry_mass())
# print(shuttle_scenario.fleet.servicers['servicer0000'].get_wet_mass())
# print('-__________________________________________')
#
# print(shuttle_scenario.fleet.servicers['servicer0000'].modules['servicer0000_phasing_propulsion'].reference_thrust)
# print(shuttle_scenario.fleet.servicers['servicer0000'].modules['servicer0000_rendezvous_propulsion'].reference_thrust)
#
#
# for _, module in shuttle_scenario.fleet.servicers['servicer0000'].modules.items():
#     print(module.id, module.get_dry_mass(), module.get_reference_power())
#     if isinstance(module, PropulsionModule):
#         print(module.initial_propellant_mass)
#
# for phase in shuttle_scenario.plan.phases:
#     print(phase.id, phase.get_delta_v())
#
# shuttle_scenario = architectures[1]['10']['1']
# print(shuttle_scenario.fleet.servicers['servicer0000'].get_dry_mass())
# print(shuttle_scenario.fleet.servicers['servicer0000'].get_wet_mass())
# print(shuttle_scenario.fleet.servicers['tanker_servicer0000'].get_dry_mass())
# print(shuttle_scenario.fleet.servicers['tanker_servicer0000'].get_wet_mass())
#
# print('-__________________________________________')
# print(shuttle_scenario.fleet.servicers['servicer0000'].modules['servicer0000_rendezvous_propulsion'].reference_thrust)
# for _, module in shuttle_scenario.fleet.servicers['servicer0000'].modules.items():
#     print(module.id, module.get_dry_mass(), module.get_reference_power())
#     if isinstance(module, PropulsionModule):
#         print(module.initial_propellant_mass)
# for _, module in shuttle_scenario.fleet.servicers['tanker_servicer0000'].modules.items():
#     print(module.id, module.get_dry_mass(), module.get_reference_power())
#     if isinstance(module, PropulsionModule):
#         print(module.initial_propellant_mass)
#
# for phase in shuttle_scenario.plan.phases:
#     print(phase.id, phase.get_delta_v())

# scenarios_names = ['Electrical shuttle', 'Chemical shuttle']

# plot snapshot
# architectures[0]['1']['1'].clients.plot_distribution(save='snapshot', save_folder='Figures')

# plot Pareto
# plot_pareto(architectures, quantity='total_cost', reference=ref[0]['1']['1'],
#             save='pareto', legend=scenarios_names, legend_loc='lower right')
#
# for architecture in architectures:
#     for tgt_per_servicer, scenarios in architecture.items():
#         print(tgt_per_servicer)
#         for number_of_servicers, scenario in scenarios.items():
#             # for _, servicer in scenario.fleet.servicers.items():
#             #     print([sat.id for sat in servicer.assigned_targets])
#             annotations = False
#             plot_timeline_from_scenario(scenario, ['get_current_rendezvous_prop_mass'], annotate=annotations)
#             plot_timeline_from_scenario(scenario, ['get_current_phasing_prop_mass'], annotate=annotations)
#             plot_timeline_from_scenario(scenario, ['r_a'], annotate=annotations)
#             plot_timeline_from_scenario(scenario, ['r_p'], annotate=annotations)
#             plot_timeline_from_scenario(scenario, ['raan'], annotate=annotations)
#     # plot_title = architecture['1']['1'].architecture + '_' + architecture['1']['1'].prop_type
#     plot_mass_summary(architecture, rm_duplicates=True, save='plot_title'+'_mass',
#                       offset_text=-10, text_limit=20)
#     plot_cost_summary(architecture, reference=ref[0]['1']['1'], save=plot_title+'_cost', offset_text=-0.5,
#                       text_limit=5)


# print([tgt.id for tgt in scenarios[3]['9']['1'].fleet.servicers['servicer0000'].assigned_targets])
# plot_timeline(scenarios[0]["1"]["1"], ['get_current_mass'])
# plot_timeline(scenarios[3]["9"]["1"], ['r_a'])
# plot_timeline(scenarios[3]["9"]["1"], ['raan'])
# plot_timeline(scenarios[3]["9"]["1"], ['get_current_mass'])

# quantities_to_plot = ['get_cost_per_target', 'get_total_cost']

# # define names
# scenarios_names = []
# for scenario in scenarios:
#     scenarios_names.append(scenario['1']['1'].architecture + "_" + scenario['1']['1'].prop_type)
# heatmap_titles = []
# for name in scenarios_names:
#     temp = []
#     for quantity in quantities_to_plot:
#         temp.append(name + " - " + quantity)
#     heatmap_titles.append(temp)
#

#
# # plot Pareto
# plot_pareto(scenarios, reference=scenarios[0]['1']['1'],
#             save='pareto', legend=scenarios_names)

# # plot heatmaps
# plot_heatmap(scenarios, quantities_to_plot,
#              scaling=1, suffix=None,
#              reference=scenarios[0]['1']['1'], valfmt='{x:.2f}',
#              save='heatmap', title=heatmap_titles)
