from app_entry_rca.reporting.writers import write_all

def run(state,config): write_all(state,state.options.get('out','app_entry_rca_out'))
